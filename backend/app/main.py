from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    organize.router, prefix="/api/v1/organize", tags=["Organisation PDF"]
)
app.include_router(modify.router, prefix="/api/v1/modify", tags=["Modification PDF"])
app.include_router(security.router, prefix="/api/v1/security", tags=["Sécurité PDF"])
app.include_router(forms.router, prefix="/api/v1/forms", tags=["Formulaires PDF"])
app.include_router(convert.router, prefix="/api/v1/convert", tags=["Conversions PDF"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["Intelligence Artificielle"])


@app.get("/health")
def health():
    return {"status": "ok"}
