import pytest

from app.tests.auth.conftest import ORIGIN, client_for, login

pytestmark = pytest.mark.anyio


@pytest.fixture
async def running(build_app, server):
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            await login(client, server)
            yield client, ctx, app


async def test_foreign_origin_is_refused(running):
    client, _, _ = running
    assert (await client.post("/api/upload", headers={"Origin": "https://evil.test"})).status_code == 403
    assert (await client.post("/api/upload", headers={"Origin": "null"})).status_code == 403


async def test_own_origin_is_accepted(running):
    client, _, _ = running
    assert (await client.post("/api/upload", headers={"Origin": ORIGIN})).status_code == 200


async def test_sec_fetch_site_is_used_when_origin_is_absent(running):
    client, _, _ = running
    assert (await client.post("/api/upload", headers={"Sec-Fetch-Site": "same-origin"})).status_code == 200
    assert (await client.post("/api/upload", headers={"Sec-Fetch-Site": "cross-site"})).status_code == 403
    assert (await client.post("/api/upload")).status_code == 403


async def test_safe_methods_need_no_origin(running):
    client, _, _ = running
    assert (await client.get("/api/private")).status_code == 200


async def test_backchannel_logout_is_exempt(running, server):
    client, _, _ = running
    response = await client.post("/auth/backchannel-logout", data={"logout_token": server.logout_token()})
    assert response.status_code == 200


async def test_logout_is_protected_by_the_origin_check(running):
    client, _, _ = running
    assert (await client.post("/auth/logout", headers={"Origin": "https://evil.test"})).status_code == 403
    assert (await client.get("/api/private")).status_code == 200


async def test_logout_deletes_the_session_and_clears_the_cookie(running):
    client, ctx, _ = running
    response = await client.post("/auth/logout", headers={"Origin": ORIGIN})
    assert response.status_code == 200 and response.json() == {"redirect": "/"}
    assert "session=" in response.headers["set-cookie"] and "Max-Age=0" in response.headers["set-cookie"]
    client.cookies.clear()
    assert (await client.get("/api/private")).status_code == 401


async def test_logout_uses_end_session_endpoint_and_revokes_the_token(build_app, server):
    server.metadata["end_session_endpoint"] = "https://auth.test/logout"
    server.metadata["revocation_endpoint"] = "https://auth.test/revoke"
    revoked = []
    original = server.handle

    async def handle(request):
        if request.url.path == "/revoke":
            revoked.append(request.content.decode())
            return __import__("httpx").Response(200)
        return await original(request)

    server.handle = handle
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            await login(client, server)
            response = await client.post("/auth/logout", headers={"Origin": ORIGIN})
    assert response.json() == {"redirect": "https://auth.test/logout"}
    assert revoked and "rt-1" in revoked[0]


async def test_logout_succeeds_even_if_the_revocation_fails(build_app, server):
    import httpx

    server.metadata["revocation_endpoint"] = "https://auth.test/revoke"
    original = server.handle

    async def handle(request):
        if request.url.path == "/revoke":
            raise httpx.ConnectError("down")
        return await original(request)

    server.handle = handle
    app, ctx = build_app()
    async with app.router.lifespan_context(app):
        async with client_for(app) as client:
            await login(client, server)
            response = await client.post("/auth/logout", headers={"Origin": ORIGIN})
            assert response.status_code == 200
            assert (await client.get("/api/private")).status_code == 401
