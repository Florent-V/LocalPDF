from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.tempfiles import create_thumbnail_job, delete_job, get_job_dir, job_workspace
from app.core.uploads import check_upload_size, validate_pdf_upload
from app.schemas.security import RedactRequest
from app.services import organize as organize_service
from app.services import security as security_service

router = APIRouter()


@router.post("/protect")
def protect(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user_password: str = Form(...),
    owner_password: str | None = Form(None),
    allow_printing: bool = Form(True),
    allow_copying: bool = Form(False),
):
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        output = ws / "protected.pdf"
        security_service.protect_pdf(
            file.file,
            output,
            user_password,
            owner_password,
            allow_printing,
            allow_copying,
        )
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
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        output = ws / "unlocked.pdf"
        security_service.unlock_pdf(file.file, output, password)
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="unlocked.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/redact/jobs")
def create_redact_job(file: UploadFile):
    check_upload_size(file)
    validate_pdf_upload(file)
    job_id, page_count, thumbs = create_thumbnail_job(file, organize_service.generate_thumbnails)
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
