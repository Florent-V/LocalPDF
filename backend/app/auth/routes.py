import logging
import re
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.requests import cookie_parser

from app.auth.client import InvalidGrant, TemporaryError
from app.auth.logout_token import InvalidToken
from app.auth.store import hash_id

log = logging.getLogger("app.auth")

router = APIRouter()

NO_STORE = {"Cache-Control": "no-store"}


def safe_return_to(value: str | None) -> str:
    """Only a path of this site: `//host` and `/\\host` are read by browsers
    as another site."""
    if not value or not value.startswith("/") or value.startswith(("//", "/\\")):
        return "/"
    if "\\" in value or any(ord(c) < 32 for c in value):
        return "/"
    return value


def _clear_cookie(response: Response, settings) -> None:
    response.delete_cookie(
        settings.cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status, headers=NO_STORE)


@router.get("/auth/login")
async def login(request: Request, return_to: str = "/"):
    ctx = request.app.state.auth
    if not ctx.discovery.ready:
        return _error(503, "oauth_server_unavailable")
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    nonce = secrets.token_urlsafe(24) if "openid" in ctx.settings.oauth_scopes.split() else None
    await ctx.store.add_login_attempt(state, code_verifier, nonce, safe_return_to(return_to))
    url = ctx.client.authorization_url(state, code_verifier, nonce)
    return RedirectResponse(url, status_code=302, headers=NO_STORE)


async def _identity(ctx, token: dict, nonce: str | None) -> dict:
    """Who just logged in: the id_token if the server sends one, else the
    userinfo endpoint, else the claims of an access token we can verify."""
    verifier = ctx.verifier
    if token.get("id_token"):
        claims = await verifier.decode_async(
            token["id_token"], issuer=ctx.settings.oauth_issuer, required=["iss", "aud", "exp", "sub"]
        )
        if nonce and claims.get("nonce") != nonce:
            raise InvalidToken("nonce mismatch")
        return claims
    if ctx.discovery.get("userinfo_endpoint"):
        return await ctx.client.userinfo(token["access_token"])
    return await verifier.decode_async(token["access_token"], issuer=None, required=["aud", "exp", "sub"])


@router.get("/auth/callback")
async def callback(request: Request):
    ctx = request.app.state.auth
    params = request.query_params

    if params.get("error"):
        code = re.sub(r"[^a-z_]", "", params["error"].lower())[:64] or "error"
        return RedirectResponse(f"/?auth_error={code}", status_code=302, headers=NO_STORE)

    if ctx.discovery.get("authorization_response_iss_parameter_supported") and params.get("iss") != ctx.settings.oauth_issuer:
        return _error(400, "invalid_issuer")

    attempt = await ctx.store.pop_login_attempt(params.get("state", ""))
    if attempt is None or not params.get("code"):
        return _error(400, "invalid_state")

    try:
        token = await ctx.client.exchange_code(params["code"], attempt.code_verifier)
        claims = await _identity(ctx, token, attempt.nonce)
    except (InvalidGrant, InvalidToken):
        return _error(400, "invalid_grant")
    except (TemporaryError, httpx.HTTPError) as exc:
        log.warning("Login failed, OAuth server error: %s", exc)
        return _error(502, "oauth_server_error")

    # The stable identifier: `id` (UUID) at this server; `sub` can change (it is the e-mail).
    sub = str(claims.get("id") or claims.get("uid") or claims["sub"])
    user_claims = {
        "name": claims.get("name") or claims.get("preferred_username") or claims.get("email"),
        "email": claims.get("email"),
        "roles": claims.get("roles") or [],
    }
    session_id = await ctx.store.create_session(
        sub=sub,
        oauth_sid=claims.get("sid"),
        user_claims=user_claims,
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token", ""),
        access_expires_at=token.get("expires_at") or 0,
    )
    response = RedirectResponse(attempt.return_to, status_code=302, headers=NO_STORE)
    response.set_cookie(
        ctx.settings.cookie_name,
        session_id,
        max_age=ctx.settings.session_absolute_ttl,
        path="/",
        secure=ctx.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


def _logout_redirect(ctx) -> str:
    """Where to send the browser to end the SSO session too.

    Standard servers publish `end_session_endpoint`. Otherwise fall back to the
    `{issuer}/logout?redirect_uri=` convention of the home OAuth server, which only
    redirects back to the origin of a registered application.
    """
    endpoint = ctx.discovery.get("end_session_endpoint")
    if endpoint:
        return endpoint
    query = urlencode({"redirect_uri": f"{ctx.settings.public_origin}/"})
    return f"{ctx.settings.oauth_issuer.rstrip('/')}/logout?{query}"


@router.post("/auth/logout")
async def logout(request: Request):
    ctx = request.app.state.auth
    session_id = cookie_parser(request.headers.get("cookie", "")).get(ctx.settings.cookie_name)
    if session_id:
        id_hash = hash_id(session_id)
        session = await ctx.store.get_session(id_hash)
        await ctx.store.delete_session(id_hash)
        if session and session.refresh_token:
            await ctx.client.revoke(session.refresh_token)
    response = JSONResponse({"redirect": _logout_redirect(ctx)}, headers=NO_STORE)
    _clear_cookie(response, ctx.settings)
    return response


@router.post("/auth/backchannel-logout")
async def backchannel_logout(request: Request):
    """Called by the OAuth server, not by a browser: no session, no CSRF check."""
    ctx = request.app.state.auth
    if not ctx.discovery.ready:
        return _error(503, "oauth_server_unavailable")
    form = await request.form()
    token = form.get("logout_token")
    if not isinstance(token, str) or not token:
        return _error(400, "invalid_request")
    try:
        claims = await ctx.verifier.verify_logout_token(token, ctx.store)
    except InvalidToken as exc:
        log.warning("Logout token refused: %s", exc)
        return _error(400, "invalid_request")
    # No sid at this server: the logout targets the whole user (stable id, then login).
    await ctx.store.delete_for_user(sid=claims.get("sid"), subs=(claims.get("uid"), claims.get("sub")))
    return Response(status_code=200, headers=NO_STORE)


@router.get("/api/me")
async def me(request: Request):
    user = request.state.user
    return JSONResponse(
        {"sub": user.sub, "name": user.name, "email": user.email, "roles": list(user.roles)},
        headers=NO_STORE,
    )
