import logging

import httpx
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.auth.config import AuthSettings
from app.auth.discovery import Discovery

log = logging.getLogger("app.auth")

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class InvalidGrant(Exception):
    """The refresh token (or code) is refused for good: expired, revoked, access removed."""


class TemporaryError(Exception):
    """Network failure or 5xx: the session must be kept and the call retried."""


class OAuthClient:
    """Authorization code + PKCE S256 client. Authlib's starlette integration
    is deliberately not used: it keeps its state in a signed cookie, which
    cannot be revoked. One httpx client (Authlib's) serves every call."""

    def __init__(self, settings: AuthSettings, discovery: Discovery, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.discovery = discovery
        self.http = AsyncOAuth2Client(
            client_id=settings.oauth_client_id,
            client_secret=settings.oauth_client_secret,
            scope=settings.oauth_scopes,
            redirect_uri=settings.redirect_uri,
            code_challenge_method="S256",
            timeout=TIMEOUT,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    def _auth_method(self) -> str:
        supported = self.discovery.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
        for method in ("client_secret_basic", "client_secret_post"):
            if method in supported:
                return method
        return "client_secret_basic"

    def authorization_url(self, state: str, code_verifier: str, nonce: str | None) -> str:
        extra = {"nonce": nonce} if nonce else {}
        url, _ = self.http.create_authorization_url(
            self.discovery.get("authorization_endpoint"), state=state, code_verifier=code_verifier, **extra
        )
        return url

    async def _token_request(self, call, *args, **kwargs) -> dict:
        self.http.token_endpoint_auth_method = self._auth_method()
        try:
            token = await call(self.discovery.get("token_endpoint"), *args, **kwargs)
        except OAuthError as exc:
            if exc.error in ("invalid_grant", "invalid_client", "unauthorized_client", "access_denied"):
                raise InvalidGrant(exc.error) from exc
            raise TemporaryError(f"{exc.error}: {exc.description}") from exc
        except httpx.HTTPError as exc:
            raise TemporaryError(str(exc)) from exc
        return dict(token)

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        return await self._token_request(
            self.http.fetch_token,
            grant_type="authorization_code",
            code=code,
            code_verifier=code_verifier,
            redirect_uri=self.settings.redirect_uri,
        )

    async def refresh(self, refresh_token: str) -> dict:
        return await self._token_request(self.http.refresh_token, refresh_token=refresh_token)

    async def revoke(self, refresh_token: str) -> None:
        """Best effort: the logout never fails because of the revocation."""
        endpoint = self.discovery.get("revocation_endpoint")
        if not endpoint:
            return
        try:
            self.http.revocation_endpoint_auth_method = self._auth_method()
            await self.http.revoke_token(endpoint, token=refresh_token, token_type_hint="refresh_token")
        except Exception as exc:
            log.warning("Token revocation failed: %s", exc)

    async def userinfo(self, access_token: str) -> dict:
        endpoint = self.discovery.get("userinfo_endpoint")
        try:
            response = await self.http.get(endpoint, headers={"Authorization": f"Bearer {access_token}"}, auth=None)
        except httpx.HTTPError as exc:
            raise TemporaryError(str(exc)) from exc
        if response.status_code in (401, 403):
            raise InvalidGrant(f"userinfo: HTTP {response.status_code}")
        if response.status_code != 200:
            raise TemporaryError(f"userinfo: HTTP {response.status_code}")
        return response.json()
