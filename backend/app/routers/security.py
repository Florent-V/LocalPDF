import shutil

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pypdf import PdfReader

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job, get_job_dir, register_job
from app.schemas.security import RedactRequest
from app.services import organize as organize_service
from app.services import security as security_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


@router.post("/protect")
def protect(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user_password: str = Form(...),
    owner_password: str | None = Form(None),
    allow_printing: bool = Form(True),
    allow_copying: bool = Form(False),
):
    _size_check(file)
    ws = create_job_dir()
    try:
        output = ws / "protected.pdf"
        security_service.protect_pdf(
            file.file,
            output,
            user_password,
            owner_password,
            allow_printing,
            allow_copying,
        )
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="protected.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/unlock")
def unlock(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    password: str = Form(...),
):
    _size_check(file)
    ws = create_job_dir()
    try:
        output = ws / "unlocked.pdf"
        security_service.unlock_pdf(file.file, output, password)
    except HTTPException:
        delete_job(ws.name)
        raise
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="unlocked.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/redact/jobs")
def create_redact_job(file: UploadFile):
    _size_check(file)
    ws = create_job_dir()
    input_path = ws / "input.pdf"
    with open(input_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    page_count = len(PdfReader(input_path).pages)
    thumbs = organize_service.generate_thumbnails(input_path, ws)
    job_id = ws.name
    register_job(ws)
    return {"job_id": job_id, "page_count": page_count, "thumbnails": thumbs}


@router.patch("/redact/jobs/{job_id}")
def apply_redact(job_id: str, request: RedactRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    output_path = ws / "result.pdf"

    if request.rectangles:
        rectangles = [r.model_dump() for r in request.rectangles]
        with open(input_path, "rb") as f:
            security_service.redact_rectangles(f, output_path, rectangles)
    elif request.terms:
        with open(input_path, "rb") as f:
            security_service.search_and_redact(f, output_path, request.terms)
    else:
        raise HTTPException(
            status_code=400, detail="Rectangles ou termes de recherche requis."
        )
    return {"job_id": job_id, "status": "ready"}


@router.get("/redact/jobs/{job_id}/download")
def download_redact_job(job_id: str, background_tasks: BackgroundTasks):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    output_path = ws / "result.pdf"
    if not output_path.exists():
        raise HTTPException(
            status_code=400, detail="Aucun résultat prêt. Appliquez d'abord la censure."
        )
    background_tasks.add_task(delete_job, job_id)
    return FileResponse(
        path=output_path,
        filename="redacted.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.delete("/redact/jobs/{job_id}")
def abandon_redact_job(job_id: str):
    delete_job(job_id)
    return {"detail": "Job supprimé."}
