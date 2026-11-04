import asyncio
import logging
import time

from starlette.datastructures import Headers
from starlette.requests import cookie_parser
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth import csrf
from app.auth.client import InvalidGrant, TemporaryError
from app.auth.deps import AuthUser
from app.auth.store import hash_id

log = logging.getLogger("app.auth")

LAST_SEEN_GRANULARITY = 60
REFRESH_LEASE = 20
WAIT_STEP = 0.1


def user_from(claims: dict) -> AuthUser:
    return AuthUser(
        sub=claims["sub"],
        name=claims.get("name"),
        email=claims.get("email"),
        roles=tuple(claims.get("roles") or ()),
    )


async def revalidate(ctx, id_hash: str) -> bool:
    """Refreshes the tokens: it proves the user still has access (the safety
    net of the back-channel logout) and rotates the refresh token. One worker
    refreshes, the others wait for it. False = session over."""
    status, session = await ctx.store.claim_refresh(
        id_hash, ctx.settings.session_revalidate_interval, REFRESH_LEASE
    )
    if status == "gone":
        return False
    if status == "fresh":
        return True
    if status == "busy":
        deadline = time.time() + REFRESH_LEASE
        while time.time() < deadline:
            await asyncio.sleep(WAIT_STEP)
            current = await ctx.store.get_session(id_hash)
            if current is None:
                return False
            if current.refresh_lease_until == 0 or current.refresh_lease_until < time.time():
                break
        return True

    try:
        token = await ctx.client.refresh(session.refresh_token)
    except InvalidGrant:
        await ctx.store.delete_session(id_hash)
        return False
    except TemporaryError as exc:
        log.warning("Token refresh failed, session kept: %s", exc)
        await ctx.store.fail_refresh(id_hash)
        return True
    await ctx.store.finish_refresh(
        id_hash,
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token") or session.refresh_token,
        access_expires_at=token.get("expires_at") or time.time() + token.get("expires_in", 900),
    )
    return True


async def authenticate(ctx, session_id: str | None) -> AuthUser | None:
    if not session_id:
        return None
    id_hash = hash_id(session_id)
    session = await ctx.store.get_session(id_hash)
    if session is None:
        return None
    now = time.time()
    if now - session.last_seen_at > ctx.settings.session_idle_ttl or now >= session.absolute_expires_at:
        await ctx.store.delete_session(id_hash)
        return None
    if now - session.last_seen_at > LAST_SEEN_GRANULARITY:
        await ctx.store.touch(id_hash)
    if now - session.last_revalidated_at >= ctx.settings.session_revalidate_interval:
        if not await revalidate(ctx, id_hash):
            return None
    return user_from({**session.user_claims, "sub": session.sub})


def _json(status: int, body: dict) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


class AuthMiddleware:
    """Pure ASGI on purpose. FastAPI parses a multipart body *before* it runs
    the dependencies, so the check has to happen here, before the body is read:
    otherwise a 200 MB unauthenticated upload would be received in full
    before getting its 401."""

    def __init__(self, app: ASGIApp, *, protected_prefixes: tuple[str, ...], public_paths: tuple[str, ...]):
        self.app = app
        self.protected_prefixes = tuple(protected_prefixes)
        self.public_paths = frozenset(public_paths)

    def _protected(self, path: str) -> bool:
        return path.startswith(self.protected_prefixes) and path not in self.public_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        ctx = scope["app"].state.auth
        path, method = scope["path"], scope["method"]
        headers = Headers(scope=scope)

        if self._protected(path):
            cookies = cookie_parser(headers.get("cookie", ""))
            user = await authenticate(ctx, cookies.get(ctx.settings.cookie_name))
            if user is None:
                await _json(401, {"error": "unauthenticated"})(scope, receive, send)
                return
            scope.setdefault("state", {})["user"] = user

        if csrf.needs_check(method, path) and not csrf.is_allowed(headers, ctx.settings.public_origin):
            await _json(403, {"error": "forbidden_origin"})(scope, receive, send)
            return

        await self.app(scope, receive, send)
