import asyncio
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

from app.core.config import settings

_job_registry: dict[str, dict] = {}
_registry_lock = Lock()
_purge_task: asyncio.Task | None = None


def create_job_dir() -> Path:
    job_id = str(uuid.uuid4())
    path = Path(settings.temp_root) / job_id
    path.mkdir(parents=True, exist_ok=True)
    with _registry_lock:
        _job_registry[job_id] = {
            "path": str(path),
            "created_at": datetime.now(timezone.utc),
            "last_access": datetime.now(timezone.utc),
        }
    return path


def get_job_dir(job_id: str) -> Path | None:
    with _registry_lock:
        job = _job_registry.get(job_id)
        if not job:
            return None
        job["last_access"] = datetime.now(timezone.utc)
    return Path(job["path"])


def register_job(path: Path) -> str:
    job_id = path.name
    with _registry_lock:
        _job_registry[job_id] = {
            "path": str(path),
            "created_at": datetime.now(timezone.utc),
            "last_access": datetime.now(timezone.utc),
        }
    return job_id


def delete_job(job_id: str) -> None:
    with _registry_lock:
        job = _job_registry.pop(job_id, None)
    if job:
        shutil.rmtree(job["path"], ignore_errors=True)


def _cleanup_expired():
    now = datetime.now(timezone.utc)
    ttl = timedelta(minutes=settings.temp_ttl_minutes)
    expired = []
    with _registry_lock:
        for job_id, meta in list(_job_registry.items()):
            if now - meta["last_access"] > ttl:
                expired.append(job_id)
    for job_id in expired:
        delete_job(job_id)


async def _purge_loop():
    while True:
        await asyncio.sleep(60)
        _cleanup_expired()


def start_purge_task():
    global _purge_task
    _purge_task = asyncio.create_task(_purge_loop())


def stop_purge_task():
    global _purge_task
    if _purge_task:
        _purge_task.cancel()


class TempWorkspace:
    """Context manager pour un traitement mono-étape. Supprime le dossier à la sortie."""

    def __init__(self):
        self.path = create_job_dir()

    def __enter__(self):
        return self.path

    def __exit__(self, exc_type, exc, tb):
        delete_job(self.path.name)
