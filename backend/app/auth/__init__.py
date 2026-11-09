import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastapi import FastAPI

from app.auth.client import OAuthClient
from app.auth.config import AuthSettings
from app.auth.discovery import Discovery, DiscoveryUnavailable
from app.auth.logout_token import TokenVerifier
from app.auth.middleware import AuthMiddleware
from app.auth.routes import router
from app.auth.store import SessionStore

AUTH_MODULE_VERSION = "2.2.0"

log = logging.getLogger("app.auth")

PURGE_INTERVAL = 600


@dataclass
class AuthContext:
    settings: AuthSettings
    store: SessionStore
    discovery: Discovery
    client: OAuthClient
    verifier: TokenVerifier


async def _purge_loop(store: SessionStore) -> None:
    while True:
        await asyncio.sleep(PURGE_INTERVAL)
        try:
            await store.purge()
        except Exception as exc:
            log.warning("Session purge failed: %s", exc)


def setup_auth(
    app: FastAPI,
    settings: AuthSettings,
    protected_prefixes: tuple[str, ...],
    public_paths: tuple[str, ...] = (),
    transport: httpx.AsyncBaseTransport | None = None,
) -> AuthContext:
    """Wires the OAuth client into a FastAPI app: /auth/* and /api/me routes,
    the session middleware and the startup (discovery, purge). Anything that
    depends on the app (which paths are protected) comes in as a parameter.

    `transport` replaces the network for the HTTP calls to the OAuth server
    (tests)."""
    # Discovery is fetched by the same Authlib/httpx client as the tokens.
    discovery = Discovery(settings, http=None)  # type: ignore[arg-type]
    client = OAuthClient(settings, discovery, transport=transport)
    discovery.http = client.http
    ctx = AuthContext(
        settings=settings,
        store=SessionStore(settings.session_db_path, settings.session_idle_ttl, settings.session_absolute_ttl),
        discovery=discovery,
        client=client,
        verifier=TokenVerifier(settings, discovery),
    )
    app.state.auth = ctx
    app.include_router(router)
    app.add_middleware(AuthMiddleware, protected_prefixes=protected_prefixes, public_paths=public_paths)

    inner = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(a: FastAPI):
        await ctx.store.init()
        try:
            await discovery.load_with_retry()
        except DiscoveryUnavailable as exc:
            # Stay up, not ready (health 503, login 503): the refresh task keeps trying.
            log.error("OAuth server unreachable at startup, will keep trying: %s", exc)
        background = [
            asyncio.create_task(discovery.keep_fresh()),
            asyncio.create_task(_purge_loop(ctx.store)),
        ]
        try:
            async with inner(a) as state:
                yield state
        finally:
            for task in background:
                task.cancel()
            for task in background:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            await client.aclose()

    app.router.lifespan_context = lifespan
    return ctx
