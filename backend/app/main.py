from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.auth import setup_auth
from app.auth.config import AuthSettings
from app.core.body_size_limit import BodySizeLimitMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.core.owner import bind_owner
from app.core.tempfiles import start_purge_task, stop_purge_task
from app.routers import ai, convert, forms, modify, organize, security


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_purge_task()
    yield
    stop_purge_task()


app = FastAPI(
    title="LocalPDF API",
    description="API locale et privacy-first de manipulation de PDF.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_upload_bytes)

# The API is its own OAuth client (BFF): sessions live server-side and the
# browser only holds an opaque cookie. Same origin as the static front (Caddy
# routes /api and /auth here), hence no CORS.
auth = setup_auth(
    app,
    AuthSettings(),
    protected_prefixes=("/api",),
    public_paths=("/api/health",),
)

# Every tool route is reserved to a logged-in user (the middleware answers 401
# before the body is read); bind_owner scopes the jobs to that user.
authenticated = [Depends(bind_owner)]
app.include_router(
    organize.router,
    prefix="/api/v1/organize",
    tags=["Organisation PDF"],
    dependencies=authenticated,
)
app.include_router(
    modify.router, prefix="/api/v1/modify", tags=["Modification PDF"], dependencies=authenticated
)
app.include_router(
    security.router, prefix="/api/v1/security", tags=["Sécurité PDF"], dependencies=authenticated
)
app.include_router(
    forms.router, prefix="/api/v1/forms", tags=["Formulaires PDF"], dependencies=authenticated
)
app.include_router(
    convert.router, prefix="/api/v1/convert", tags=["Conversions PDF"], dependencies=authenticated
)
app.include_router(
    ai.router, prefix="/api/v1/ai", tags=["Intelligence Artificielle"], dependencies=authenticated
)


@app.get("/api/health")
def health():
    # Not ready until the OAuth server's metadata has been read.
    if not auth.discovery.ready:
        return JSONResponse({"status": "oauth_unavailable"}, status_code=503)
    return {"status": "ok"}
