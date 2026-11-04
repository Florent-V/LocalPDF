import sqlite3
from urllib.parse import parse_qs, urlparse

import pytest

from app.auth.routes import safe_return_to
from app.auth.store import hash_id
from app.tests.auth.conftest import ORIGIN, client_for, login
from app.tests.auth.fake_server import CLIENT_ID

pytestmark = pytest.mark.anyio


@pytest.fixture
async def running(build_app):
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            yield client, ctx, app


async def test_login_redirects_with_pkce_s256_and_state(running):
    client, _, _ = running
    response = await client.get("/auth/login")
    assert response.status_code == 302
    url = urlparse(response.headers["location"])
    query = parse_qs(url.query)
    assert url.path == "/authorize"
    assert query["code_challenge_method"] == ["S256"]
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [f"{ORIGIN}/auth/callback"]
    assert query["response_type"] == ["code"]
    assert len(query["state"][0]) >= 32 and "code_challenge" in query


@pytest.mark.parametrize("value", ["//evil.com", "https://evil.com", "/\\evil.com", "evil", "/a\\b", "/a\nb", None, ""])
def test_malicious_return_to_falls_back_to_root(value):
    assert safe_return_to(value) == "/"


def test_local_return_to_is_kept():
    assert safe_return_to("/tools/merge?x=1") == "/tools/merge?x=1"


async def test_login_stores_a_session_and_goes_back_to_return_to(running, server):
    client, ctx, _ = running
    response = await login(client, server, return_to="/tools/merge")
    assert response.status_code == 302
    assert response.headers["location"] == "/tools/merge"
    me = await client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == {"sub": "uid-alice", "name": "alice", "email": "alice@example.com", "roles": []}


async def test_cookie_attributes_and_no_token_in_it(running, server):
    client, ctx, _ = running
    response = await login(client, server)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("session=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    value = cookie.split(";")[0].split("=", 1)[1]
    assert "at-" not in value and "rt-" not in value
    # Only the hash is in the database, tokens are server-side.
    db = sqlite3.connect(ctx.settings.session_db_path)
    ids = [row[0] for row in db.execute("SELECT id_hash FROM sessions")]
    assert ids == [hash_id(value)] and value not in ids


async def test_prod_cookie_is_host_prefixed_and_secure(build_app, server):
    app, _ = build_app(app_env="prod", cookie_secure=True)
    server.metadata["issuer"] = server.metadata["issuer"]  # https already
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            response = await login(client, server)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("__Host-session=") and "Secure" in cookie


async def test_session_id_changes_at_every_login(running, server):
    client, ctx, _ = running
    first = (await login(client, server)).headers["set-cookie"].split(";")[0]
    second = (await login(client, server)).headers["set-cookie"].split(";")[0]
    assert first != second


async def test_unknown_state_is_refused(running):
    client, _, _ = running
    assert (await client.get("/auth/callback", params={"code": "x", "state": "nope"})).status_code == 400


async def test_replayed_state_is_refused(running, server):
    client, _, _ = running
    response = await client.get("/auth/login")
    query = parse_qs(urlparse(response.headers["location"]).query)
    params = {"code": server.authorize(query), "state": query["state"][0]}
    assert (await client.get("/auth/callback", params=params)).status_code == 302
    assert (await client.get("/auth/callback", params=params)).status_code == 400


async def test_expired_state_is_refused(running, server):
    client, ctx, _ = running
    response = await client.get("/auth/login")
    query = parse_qs(urlparse(response.headers["location"]).query)
    db = sqlite3.connect(ctx.settings.session_db_path)
    db.execute("UPDATE login_attempts SET expires_at = 0")
    db.commit()
    params = {"code": server.authorize(query), "state": query["state"][0]}
    assert (await client.get("/auth/callback", params=params)).status_code == 400


async def test_oauth_error_redirects_without_looping(running):
    client, _, _ = running
    response = await client.get("/auth/callback", params={"error": "access_denied", "state": "x"})
    assert response.status_code == 302
    assert response.headers["location"] == "/?auth_error=access_denied"


async def test_wrong_code_verifier_is_refused_by_the_server(running, server):
    client, _, _ = running
    response = await client.get("/auth/login")
    query = parse_qs(urlparse(response.headers["location"]).query)
    server.authorize(query)
    server.codes["code-1"] = "another-challenge"
    response = await client.get("/auth/callback", params={"code": "code-1", "state": query["state"][0]})
    assert response.status_code == 400 and response.json() == {"error": "invalid_grant"}


async def test_iss_parameter_is_checked_when_the_server_announces_it(build_app, server):
    server.metadata["authorization_response_iss_parameter_supported"] = True
    app, _ = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            response = await client.get("/auth/login")
            query = parse_qs(urlparse(response.headers["location"]).query)
            params = {"code": server.authorize(query), "state": query["state"][0]}
            assert (await client.get("/auth/callback", params={**params, "iss": "https://evil.test"})).status_code == 400
            response = await client.get("/auth/login")
            query = parse_qs(urlparse(response.headers["location"]).query)
            params = {"code": server.authorize(query), "state": query["state"][0], "iss": server.metadata["issuer"]}
            assert (await client.get("/auth/callback", params=params)).status_code == 302
