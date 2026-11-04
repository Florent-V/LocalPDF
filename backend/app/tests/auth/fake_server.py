import base64
import hashlib
import json
import time
import asyncio
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://auth.test"
CLIENT_ID = "localpdf-test"
CLIENT_SECRET = "test-secret"
EVENT = "http://schemas.openid.net/event/backchannel-logout"


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeOAuthServer:
    """An OAuth server in memory: discovery document, JWKS, /token (code +
    PKCE, refresh with rotation) and /userinfo, behind an httpx transport."""

    def __init__(self):
        self.key = new_key()
        self.kid = "key-1"
        self.metadata = {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "userinfo_endpoint": f"{ISSUER}/api/userinfo",
            "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        }
        self.userinfo = {"sub": "alice@example.com", "id": "uid-alice", "name": "alice", "email": "alice@example.com"}
        self.well_known_path = "/.well-known/oauth-authorization-server"
        self.refresh_mode = "ok"  # ok | invalid_grant | unavailable | down
        self.refresh_delay = 0.0
        self.refresh_calls = 0
        self.discovery_calls = 0
        self.codes: dict[str, str] = {}  # code -> PKCE challenge
        self.refresh_tokens: set[str] = set()
        self.counter = 0

    # --- keys and tokens ------------------------------------------------

    def jwks(self, extra_keys=()):
        keys = []
        for kid, key in [(self.kid, self.key), *extra_keys]:
            jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
            keys.append({**jwk, "kid": kid, "use": "sig", "alg": "RS256"})
        return {"keys": keys}

    def logout_token(self, *, key=None, kid=None, algorithm="RS256", **overrides) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER, "aud": CLIENT_ID, "iat": now, "exp": now + 120,
            "jti": f"jti-{time.time_ns()}", "sub": "alice@example.com", "uid": "uid-alice",
            "events": {EVENT: {}},
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or self.key, algorithm=algorithm, headers={"kid": kid or self.kid})

    # --- authorization endpoint (the browser's part of the flow) --------

    def authorize(self, query: dict[str, list[str]]) -> str:
        """Checks what the app sent to /authorize and returns an authorization code."""
        assert query["code_challenge_method"] == ["S256"]
        assert query["client_id"] == [CLIENT_ID]
        code = f"code-{len(self.codes) + 1}"
        self.codes[code] = query["code_challenge"][0]
        return code

    # --- HTTP -----------------------------------------------------------

    def _token(self):
        self.counter += 1
        refresh = f"rt-{self.counter}"
        self.refresh_tokens.add(refresh)
        return {"access_token": f"at-{self.counter}", "token_type": "Bearer", "expires_in": 900, "refresh_token": refresh}

    @staticmethod
    def _error(status, error):
        return httpx.Response(status, json={"error": error})

    async def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/.well-known/") and path.endswith("jwks.json"):
            return httpx.Response(200, json=self.jwks())
        if path == self.well_known_path:
            self.discovery_calls += 1
            if self.refresh_mode == "down":
                raise httpx.ConnectError("down")
            return httpx.Response(200, json=self.metadata)
        if path.startswith("/.well-known/"):
            return httpx.Response(404)
        if path == "/api/userinfo":
            if request.headers.get("authorization", "").startswith("Bearer at-"):
                return httpx.Response(200, json=self.userinfo)
            return httpx.Response(401)
        if path == "/token":
            return await self._token_endpoint(request)
        return httpx.Response(404)

    async def _token_endpoint(self, request):
        expected = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        if request.headers.get("authorization") != f"Basic {expected}":
            return self._error(401, "invalid_client")
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        if form["grant_type"] == "authorization_code":
            challenge = self.codes.pop(form.get("code", ""), None)
            verifier = form.get("code_verifier", "")
            digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            if challenge is None or challenge != digest:
                return self._error(400, "invalid_grant")
            return httpx.Response(200, json=self._token())
        if form["grant_type"] == "refresh_token":
            self.refresh_calls += 1
            if self.refresh_delay:
                await asyncio.sleep(self.refresh_delay)
            if self.refresh_mode == "down":
                raise httpx.ConnectError("down")
            if self.refresh_mode == "unavailable":
                return self._error(503, "temporarily_unavailable")
            if self.refresh_mode == "invalid_grant" or form["refresh_token"] not in self.refresh_tokens:
                return self._error(400, "invalid_grant")
            self.refresh_tokens.discard(form["refresh_token"])  # single use
            return httpx.Response(200, json=self._token())
        return self._error(400, "unsupported_grant_type")
