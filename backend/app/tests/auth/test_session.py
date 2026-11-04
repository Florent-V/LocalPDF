import asyncio
import sqlite3

import pytest

from app.auth.middleware import AuthMiddleware
from app.tests.auth.conftest import client_for, login

pytestmark = pytest.mark.anyio


@pytest.fixture
async def running(build_app, server):
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            yield client, ctx, app


def db_update(ctx, sql, *args):
    db = sqlite3.connect(ctx.settings.session_db_path)
    db.execute(sql, args)
    db.commit()
    db.close()


async def test_protected_paths_need_a_session_and_public_ones_do_not(running, server):
    client, _, _ = running
    assert (await client.get("/api/open")).status_code == 200
    response = await client.get("/api/private")
    assert response.status_code == 401 and response.json() == {"error": "unauthenticated"}
    await login(client, server)
    assert (await client.get("/api/private")).status_code == 200


async def test_unauthenticated_upload_is_refused_without_reading_the_body(running):
    _, _, app = running
    body_reads = 0

    async def receive():
        nonlocal body_reads
        body_reads += 1
        return {"type": "http.request", "body": b"x" * 1024, "more_body": True}

    sent = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "method": "POST", "path": "/api/upload", "raw_path": b"/api/upload",
        "query_string": b"", "headers": [(b"origin", b"http://localhost:3010"), (b"content-length", b"209715200")],
        "app": app, "http_version": "1.1", "scheme": "http", "server": ("localhost", 80), "client": ("1.2.3.4", 1),
    }
    await app(scope, receive, send)
    assert sent[0]["status"] == 401
    assert body_reads == 0


async def test_unknown_cookie_is_unauthenticated(running):
    client, _, _ = running
    client.cookies.set("session", "forged")
    assert (await client.get("/api/private")).status_code == 401


async def test_idle_timeout_closes_the_session(running, server):
    client, ctx, _ = running
    await login(client, server)
    db_update(ctx, "UPDATE sessions SET last_seen_at = last_seen_at - ?", ctx.settings.session_idle_ttl + 5)
    assert (await client.get("/api/private")).status_code == 401
    assert (await client.get("/api/private")).status_code == 401


async def test_absolute_timeout_closes_the_session(running, server):
    client, ctx, _ = running
    await login(client, server)
    db_update(ctx, "UPDATE sessions SET absolute_expires_at = 1")
    assert (await client.get("/api/private")).status_code == 401


async def test_revalidation_rotates_the_tokens(running, server):
    client, ctx, _ = running
    await login(client, server)
    assert server.refresh_calls == 0
    db_update(ctx, "UPDATE sessions SET last_revalidated_at = last_revalidated_at - ?", ctx.settings.session_revalidate_interval + 1)
    assert (await client.get("/api/private")).status_code == 200
    assert server.refresh_calls == 1
    # Fresh again: no new refresh on the next request.
    assert (await client.get("/api/private")).status_code == 200
    assert server.refresh_calls == 1
    db = sqlite3.connect(ctx.settings.session_db_path)
    assert db.execute("SELECT refresh_token FROM sessions").fetchone()[0] == "rt-2"


async def test_invalid_grant_ends_the_session(running, server):
    client, ctx, _ = running
    await login(client, server)
    server.refresh_mode = "invalid_grant"
    db_update(ctx, "UPDATE sessions SET last_revalidated_at = 0")
    assert (await client.get("/api/private")).status_code == 401
    db = sqlite3.connect(ctx.settings.session_db_path)
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


@pytest.mark.parametrize("mode", ["down", "unavailable"])
async def test_network_error_keeps_the_session(running, server, mode):
    client, ctx, _ = running
    await login(client, server)
    server.refresh_mode = mode
    db_update(ctx, "UPDATE sessions SET last_revalidated_at = 0")
    assert (await client.get("/api/private")).status_code == 200
    db = sqlite3.connect(ctx.settings.session_db_path)
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


async def test_concurrent_requests_trigger_a_single_refresh(running, server):
    client, ctx, _ = running
    await login(client, server)
    server.refresh_delay = 0.3
    db_update(ctx, "UPDATE sessions SET last_revalidated_at = 0")
    responses = await asyncio.gather(*[client.get("/api/private") for _ in range(8)])
    assert [r.status_code for r in responses] == [200] * 8
    assert server.refresh_calls == 1


def test_middleware_is_pure_asgi():
    from starlette.middleware.base import BaseHTTPMiddleware

    assert not issubclass(AuthMiddleware, BaseHTTPMiddleware)
