import json

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job
from app.services import modify as modify_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


@router.post("/rotate")
def rotate(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    angle: int = Form(...),
    pages: str = Form(""),
    rotations: str = Form(""),
):
    _size_check(file)

    rotations_map = None
    if rotations.strip():
        try:
            parsed = json.loads(rotations)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="rotations must be valid JSON.")
        rotations_map = {int(k): int(v) for k, v in parsed.items()}

    if rotations_map is None:
        page_list = [int(p.strip()) for p in pages.split(",") if p.strip()] or None
        if angle not in (90, 180, 270):
            raise HTTPException(status_code=400, detail="Angle must be 90, 180 or 270.")

    ws = create_job_dir()
    try:
        output = ws / "rotated.pdf"
        if rotations_map is not None:
            modify_service.rotate_pdf_map(file.file, output, rotations_map)
        else:
            modify_service.rotate_pdf(file.file, output, angle, page_list)
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="rotated.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/watermark")
def watermark(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    text: str | None = Form(None),
    image: UploadFile | None = None,
    position: str = Form("center"),
    opacity: float = Form(0.3),
    width: int | None = Form(None),
    pages: str = Form(""),
):
    _size_check(file)
    if image:
        _size_check(image)
    if not text and not image:
        raise HTTPException(
            status_code=400, detail="Texte ou image requis pour le filigrane."
        )

    page_list = [int(p.strip()) for p in pages.split(",") if p.strip()] or None
    ws = create_job_dir()
    try:
        output = ws / "watermarked.pdf"
        if text:
            modify_service.add_text_watermark(
                file.file, output, text, position, opacity, page_list
            )
        else:
            modify_service.add_image_watermark(
                file.file, output, image.file, position, opacity, width, page_list
            )
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="watermarked.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
