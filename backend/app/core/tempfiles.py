import asyncio
import shutil
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

from fastapi import UploadFile
from pypdf import PdfReader

from app.core.config import settings

_job_registry: dict[str, dict] = {}
_registry_lock = Lock()
_purge_task: asyncio.Task | None = None

# uid of the authenticated user of the current request (set by
# app.core.owner.bind_owner). Jobs are scoped to it: another user's job_id
# behaves exactly like an unknown or expired one.
current_owner: ContextVar[str | None] = ContextVar("current_owner", default=None)


def create_job_dir() -> Path:
    job_id = str(uuid.uuid4())
    path = Path(settings.temp_root) / job_id
    path.mkdir(parents=True, exist_ok=True)
    with _registry_lock:
        _job_registry[job_id] = {
            "path": str(path),
            "owner": current_owner.get(),
            "created_at": datetime.now(UTC),
            "last_access": datetime.now(UTC),
        }
    return path


def get_job_dir(job_id: str) -> Path | None:
    with _registry_lock:
        job = _job_registry.get(job_id)
        if not job or job["owner"] != current_owner.get():
            return None
        job["last_access"] = datetime.now(UTC)
    return Path(job["path"])


def register_job(path: Path) -> str:
    job_id = path.name
    with _registry_lock:
        _job_registry[job_id] = {
            "path": str(path),
            "owner": current_owner.get(),
            "created_at": datetime.now(UTC),
            "last_access": datetime.now(UTC),
        }
    return job_id


def delete_job(job_id: str) -> None:
    with _registry_lock:
        job = _job_registry.get(job_id)
        if not job or job["owner"] != current_owner.get():
            return
    _purge_job(job_id)


def _purge_job(job_id: str) -> None:
    with _registry_lock:
        job = _job_registry.pop(job_id, None)
    if job:
        shutil.rmtree(job["path"], ignore_errors=True)


def _cleanup_expired():
    now = datetime.now(UTC)
    ttl = timedelta(minutes=settings.temp_ttl_minutes)
    expired = []
    with _registry_lock:
        for job_id, meta in list(_job_registry.items()):
            if now - meta["last_access"] > ttl:
                expired.append(job_id)
    for job_id in expired:
        _purge_job(job_id)


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


@contextmanager
def job_workspace():
    """Create a job dir; delete it automatically if the block raises.

    On success the workspace is left in place — the caller schedules its
    eventual cleanup (typically `background_tasks.add_task(delete_job,
    ws.name)`) once the response referencing its files has been built.
    """
    ws = create_job_dir()
    try:
        yield ws
    except Exception:
        delete_job(ws.name)
        raise


def create_thumbnail_job(
    file: UploadFile, thumbnail_fn: Callable[[Path, Path], list[str]]
) -> tuple[str, int, list[str]]:
    """Saves the upload as a registered job, page-counts it, and generates
    thumbnails via `thumbnail_fn` — the "create job + save input.pdf + count
    pages + register" sequence previously duplicated between the organize
    and redact job-creation endpoints.
    """
    with job_workspace() as ws:
        input_path = ws / "input.pdf"
        with open(input_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        page_count = len(PdfReader(input_path).pages)
        thumbs = thumbnail_fn(input_path, ws)
        job_id = ws.name
        register_job(ws)
    return job_id, page_count, thumbs
