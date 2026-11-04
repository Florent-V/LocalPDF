from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from fastapi import FastAPI

from app.auth import setup_auth
from app.auth.config import AuthSettings
from app.tests.auth.fake_server import CLIENT_ID, CLIENT_SECRET, ISSUER, FakeOAuthServer

ORIGIN = "http://localhost:3010"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def server(monkeypatch):
    fake = FakeOAuthServer()
    # PyJWKClient is synchronous (urllib): serve it the fake JWKS directly.
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: fake.jwks(getattr(fake, "extra_keys", ())))
    return fake


@pytest.fixture
def settings(tmp_path):
    def build(**overrides):
        values = {
            "oauth_issuer": ISSUER, "oauth_client_id": CLIENT_ID, "oauth_client_secret": CLIENT_SECRET,
            "public_origin": ORIGIN, "session_db_path": str(tmp_path / "sessions.db"),
            "app_env": "dev", "cookie_secure": False,
        }
        return AuthSettings(**{**values, **overrides})

    return build


@pytest.fixture
def build_app(server, settings):
    def build(**overrides):
        app = FastAPI()
        cfg = settings(**overrides)
        ctx = setup_auth(app, cfg, ("/api",), ("/api/open",), transport=httpx.MockTransport(server.handle))

        @app.get("/api/open")
        async def open_route():
            return {"open": True}

        @app.get("/api/private")
        async def private_route():
            return {"private": True}

        @app.post("/api/upload")
        async def upload_route():
            return {"uploaded": True}

        return app, ctx

    return build


def client_for(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN)


async def login(client: httpx.AsyncClient, server: FakeOAuthServer, return_to: str = "/") -> httpx.Response:
    """The whole browser flow: /auth/login, the OAuth server's authorization, /auth/callback."""
    response = await client.get("/auth/login", params={"return_to": return_to})
    assert response.status_code == 302, response.text
    query = parse_qs(urlparse(response.headers["location"]).query)
    code = server.authorize(query)
    return await client.get("/auth/callback", params={"code": code, "state": query["state"][0]})
