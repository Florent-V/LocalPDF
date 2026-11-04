import json

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.tempfiles import delete_job, job_workspace
from app.core.uploads import check_upload_size, validate_image_upload, validate_pdf_upload
from app.services import modify as modify_service

router = APIRouter()


def _parse_page_list(pages: str) -> list[int] | None:
    return [int(p.strip()) for p in pages.split(",") if p.strip()] or None


@router.post("/rotate")
def rotate(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    angle: int = Form(...),
    pages: str = Form(""),
    rotations: str = Form(""),
):
    check_upload_size(file)
    validate_pdf_upload(file)

    rotations_map = None
    if rotations.strip():
        try:
            parsed = json.loads(rotations)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="rotations must be valid JSON.")
        rotations_map = {int(k): int(v) for k, v in parsed.items()}

    if rotations_map is None:
        page_list = _parse_page_list(pages)
        if angle not in (90, 180, 270):
            raise HTTPException(status_code=400, detail="Angle must be 90, 180 or 270.")

    with job_workspace() as ws:
        output = ws / "rotated.pdf"
        if rotations_map is not None:
            modify_service.rotate_pdf_map(file.file, output, rotations_map)
        else:
            modify_service.rotate_pdf(file.file, output, angle, page_list)
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
    check_upload_size(file)
    validate_pdf_upload(file)
    if image:
        check_upload_size(image)
        validate_image_upload(image)
    if not text and not image:
        raise HTTPException(
            status_code=400, detail="Texte ou image requis pour le filigrane."
        )

    page_list = _parse_page_list(pages)
    with job_workspace() as ws:
        output = ws / "watermarked.pdf"
        if text:
            modify_service.add_text_watermark(
                file.file, output, text, position, opacity, page_list
            )
        else:
            modify_service.add_image_watermark(
                file.file, output, image.file, position, opacity, width, page_list
            )
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="watermarked.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
