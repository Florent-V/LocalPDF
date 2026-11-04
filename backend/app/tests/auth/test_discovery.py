import pytest

from app.auth.discovery import DiscoveryError, DiscoveryUnavailable, candidate_urls
from app.tests.auth.conftest import client_for
from app.tests.auth.fake_server import ISSUER

pytestmark = pytest.mark.anyio


async def start(build_app, **overrides):
    app, ctx = build_app(**overrides)
    return app, ctx


async def test_startup_reads_the_metadata(build_app):
    app, ctx = await start(build_app)
    async with app.router.lifespan_context(app):
        assert ctx.discovery.ready
        assert ctx.discovery.get("token_endpoint") == f"{ISSUER}/token"


async def test_issuer_differing_by_a_trailing_slash_blocks_startup(build_app):
    app, ctx = await start(build_app, oauth_issuer=f"{ISSUER}/")
    with pytest.raises(DiscoveryError, match="issuer mismatch"):
        async with app.router.lifespan_context(app):
            pass


async def test_missing_s256_blocks_startup(build_app, server):
    server.metadata["code_challenge_methods_supported"] = ["plain"]
    app, _ = await start(build_app)
    with pytest.raises(DiscoveryError, match="S256"):
        async with app.router.lifespan_context(app):
            pass


async def test_http_endpoints_are_refused_outside_dev(build_app, server):
    server.metadata["issuer"] = "http://auth.test"
    server.metadata["authorization_endpoint"] = "http://auth.test/authorize"
    app, _ = await start(build_app, oauth_issuer="http://auth.test", app_env="prod", cookie_secure=True)
    with pytest.raises(DiscoveryError, match="must be https"):
        async with app.router.lifespan_context(app):
            pass


async def test_no_jwks_uri_requires_the_logout_token_secret(build_app, server):
    del server.metadata["jwks_uri"]
    app, _ = await start(build_app)
    with pytest.raises(DiscoveryError, match="OAUTH_LOGOUT_TOKEN_SECRET"):
        async with app.router.lifespan_context(app):
            pass
    app, _ = await start(build_app, oauth_logout_token_secret="s3cret")
    async with app.router.lifespan_context(app):
        pass


async def test_falls_back_to_openid_configuration(build_app, server):
    server.well_known_path = "/.well-known/openid-configuration"
    app, ctx = await start(build_app)
    async with app.router.lifespan_context(app):
        assert ctx.discovery.ready


def test_issuer_with_a_path_uses_both_conventions():
    assert candidate_urls("https://a.test/oauth") == [
        "https://a.test/.well-known/oauth-authorization-server/oauth",
        "https://a.test/oauth/.well-known/openid-configuration",
    ]


@pytest.fixture
def no_backoff(monkeypatch):
    async def instant(_):
        return None

    monkeypatch.setattr("app.auth.discovery.asyncio.sleep", instant)


async def test_unreachable_server_leaves_the_app_up_but_not_ready(build_app, server, no_backoff):
    server.refresh_mode = "down"
    app, ctx = await start(build_app)
    async with app.router.lifespan_context(app):
        assert not ctx.discovery.ready
        async with client_for(app) as client:
            assert (await client.get("/auth/login")).status_code == 503


async def test_failed_refresh_keeps_the_previous_metadata(build_app, server):
    app, ctx = await start(build_app)
    async with app.router.lifespan_context(app):
        server.refresh_mode = "down"
        with pytest.raises(DiscoveryUnavailable):
            await ctx.discovery.load()
        assert ctx.discovery.ready
        assert ctx.discovery.get("token_endpoint") == f"{ISSUER}/token"


async def test_retries_with_backoff_then_gives_up(build_app, server):
    server.refresh_mode = "down"
    _, ctx = await start(build_app)
    with pytest.raises(DiscoveryUnavailable):
        await ctx.discovery.load_with_retry(attempts=3, base_delay=0)
    assert server.discovery_calls == 3
