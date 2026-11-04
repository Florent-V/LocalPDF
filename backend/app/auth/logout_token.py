import time

import jwt
from jwt import PyJWKClient
from starlette.concurrency import run_in_threadpool

from app.auth.config import AuthSettings
from app.auth.discovery import Discovery
from app.auth.store import SessionStore

BACKCHANNEL_EVENT = "http://schemas.openid.net/event/backchannel-logout"
IAT_TOLERANCE = 300
DEFAULT_ALGORITHMS = ["RS256"]


class InvalidToken(Exception):
    pass


class TokenVerifier:
    """Verifies the JWTs signed by the OAuth server (logout tokens, and the
    id_token / access token when they are used to identify the user), with
    the keys of its `jwks_uri`. PyJWKClient caches them and follows a rotation
    through the `kid` header."""

    def __init__(self, settings: AuthSettings, discovery: Discovery):
        self.settings = settings
        self.discovery = discovery
        self._jwks: dict[str, PyJWKClient] = {}

    def _key_and_algorithms(self, token: str):
        jwks_uri = self.discovery.get("jwks_uri")
        algorithms = [
            alg for alg in self.discovery.get("id_token_signing_alg_values_supported") or DEFAULT_ALGORITHMS
            if alg.lower() != "none"
        ]
        if jwks_uri:
            client = self._jwks.get(jwks_uri) or self._jwks.setdefault(
                jwks_uri, PyJWKClient(jwks_uri, cache_keys=True, lifespan=3600)
            )
            # A public key must never be usable as an HMAC secret.
            algorithms = [alg for alg in algorithms if not alg.upper().startswith("HS")] or DEFAULT_ALGORITHMS
            return client.get_signing_key_from_jwt(token).key, algorithms
        return self.settings.oauth_logout_token_secret, ["HS256"]

    def decode(self, token: str, *, issuer: str | None, required: list[str]) -> dict:
        """Blocking (PyJWKClient is synchronous): call it through a thread pool."""
        try:
            key, algorithms = self._key_and_algorithms(token)
            return jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience=self.settings.oauth_client_id,
                issuer=issuer,
                options={"require": required},
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken(str(exc)) from exc

    async def decode_async(self, token: str, *, issuer: str | None, required: list[str]) -> dict:
        return await run_in_threadpool(self.decode, token, issuer=issuer, required=required)

    async def verify_logout_token(self, token: str, store: SessionStore) -> dict:
        claims = await self.decode_async(token, issuer=self.settings.oauth_issuer, required=["iss", "aud", "iat", "jti"])
        if abs(time.time() - claims["iat"]) > IAT_TOLERANCE:
            raise InvalidToken("iat out of range")
        if BACKCHANNEL_EVENT not in (claims.get("events") or {}):
            raise InvalidToken("backchannel-logout event missing")
        if "nonce" in claims:
            raise InvalidToken("nonce must not be present in a logout token")
        if not (claims.get("sub") or claims.get("sid") or claims.get("uid")):
            raise InvalidToken("sub or sid missing")
        if not await store.mark_jti(claims["jti"], time.time() + 2 * IAT_TOLERANCE):
            raise InvalidToken("logout token already used")
        return claims
