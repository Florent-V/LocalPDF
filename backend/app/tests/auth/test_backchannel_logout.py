import sqlite3
import time

import pytest

from app.tests.auth.conftest import client_for, login
from app.tests.auth.fake_server import new_key

pytestmark = pytest.mark.anyio


@pytest.fixture
async def running(build_app, server):
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            await login(client, server)
            yield client, ctx, app


async def post(client, token):
    return await client.post("/auth/backchannel-logout", data={"logout_token": token})


async def sessions(ctx):
    db = sqlite3.connect(ctx.settings.session_db_path)
    return db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]


async def test_valid_token_closes_the_user_sessions(running, server):
    client, ctx, _ = running
    assert (await client.get("/api/private")).status_code == 200
    response = await post(client, server.logout_token())
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert (await client.get("/api/private")).status_code == 401


async def test_token_without_matching_user_changes_nothing(running, server):
    client, ctx, _ = running
    assert (await post(client, server.logout_token(sub="bob@example.com", uid="uid-bob"))).status_code == 200
    assert await sessions(ctx) == 1


async def test_sid_targets_a_single_session(running, server):
    client, ctx, _ = running
    db = sqlite3.connect(ctx.settings.session_db_path)
    db.execute("UPDATE sessions SET oauth_sid = 'sid-1'")
    db.commit()
    await post(client, server.logout_token(sid="other-sid"))
    assert await sessions(ctx) == 1
    await post(client, server.logout_token(sid="sid-1"))
    assert await sessions(ctx) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "another-app"},
        {"iss": "https://evil.test"},
        {"nonce": "n"},
        {"events": None},
        {"events": {"other": {}}},
        {"jti": None},
        {"iat": int(time.time()) - 3600},
        {"exp": int(time.time()) - 10},
        {"sub": None, "uid": None},
    ],
    ids=["aud", "iss", "nonce", "no-events", "wrong-event", "no-jti", "old-iat", "expired", "no-subject"],
)
async def test_invalid_claims_are_refused(running, server, overrides):
    client, ctx, _ = running
    assert (await post(client, server.logout_token(**overrides))).status_code == 400
    assert await sessions(ctx) == 1


async def test_wrong_signature_is_refused(running, server):
    client, ctx, _ = running
    assert (await post(client, server.logout_token(key=new_key()))).status_code == 400
    assert await sessions(ctx) == 1


async def test_alg_none_is_refused(running, server):
    import jwt

    now = int(time.time())
    token = jwt.encode(
        {"iss": "https://auth.test", "aud": "localpdf-test", "iat": now, "jti": "j", "sub": "x",
         "events": {"http://schemas.openid.net/event/backchannel-logout": {}}},
        key=None, algorithm="none",
    )
    client, ctx, _ = running
    assert (await post(client, token)).status_code == 400
    assert await sessions(ctx) == 1


async def test_unknown_kid_is_refused(running, server):
    client, ctx, _ = running
    assert (await post(client, server.logout_token(kid="unknown"))).status_code == 400
    assert await sessions(ctx) == 1


async def test_replayed_jti_is_refused(running, server):
    client, ctx, _ = running
    token = server.logout_token(sub="bob@example.com", uid="uid-bob")
    assert (await post(client, token)).status_code == 200
    assert (await post(client, token)).status_code == 400


async def test_key_rotation_is_followed_without_restart(running, server):
    client, ctx, _ = running
    new = new_key()
    server.extra_keys = [("key-2", new)]
    token = server.logout_token(key=new, kid="key-2")
    assert (await post(client, token)).status_code == 200
    assert await sessions(ctx) == 0


async def test_missing_token_is_a_bad_request(running):
    client, _, _ = running
    assert (await client.post("/auth/backchannel-logout", data={})).status_code == 400


async def test_hs256_fallback_when_the_server_has_no_jwks(build_app, server):
    import jwt

    del server.metadata["jwks_uri"]
    app, ctx = build_app(oauth_logout_token_secret="s" * 32)
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            await login(client, server)
            now = int(time.time())
            claims = {"iss": "https://auth.test", "aud": "localpdf-test", "iat": now, "jti": "hs", "uid": "uid-alice",
                      "events": {"http://schemas.openid.net/event/backchannel-logout": {}}}
            bad = jwt.encode(claims, "x" * 32, algorithm="HS256")
            assert (await post(client, bad)).status_code == 400
            good = jwt.encode({**claims, "jti": "hs2"}, "s" * 32, algorithm="HS256")
            assert (await post(client, good)).status_code == 200
            assert await sessions(ctx) == 0
