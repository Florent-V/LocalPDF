from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.archives import build_zip
from app.core.tempfiles import delete_job, job_workspace
from app.core.uploads import check_upload_size, validate_image_upload, validate_pdf_upload
from app.services import convert as convert_service

router = APIRouter()

MARKDOWN_MAX_FILE_BYTES = 20 * 1024 * 1024


@router.post("/images-to-pdf")
def images_to_pdf(files: list[UploadFile], background_tasks: BackgroundTasks):
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="Au moins une image est requise.")
    with job_workspace() as ws:
        output = ws / "images.pdf"
        images = []
        for upload in files:
            check_upload_size(upload)
            validate_image_upload(upload)
            images.append((upload.filename or "image", upload.file))
        convert_service.images_to_pdf(images, output)
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="images.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/pdf-to-images")
def pdf_to_images(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    dpi: int = Form(150),
    fmt: str = Form("png"),
):
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        result_files = convert_service.pdf_to_images(file.file, ws, dpi, fmt)
        zip_path = ws / "images.zip"
        build_zip(zip_path, result_files)

    background_tasks.add_task(delete_job, ws.name)

    def iterfile():
        with open(zip_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=images.zip"},
        background=background_tasks,
    )


@router.post("/office-to-pdf")
def office_to_pdf(
    file: UploadFile,
    background_tasks: BackgroundTasks,
):
    check_upload_size(file)
    with job_workspace() as ws:
        output = convert_service.office_to_pdf(
            file.file, ws, file.filename or "document.docx"
        )
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="converted.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/pdf-to-word")
def pdf_to_word(file: UploadFile, background_tasks: BackgroundTasks):
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        output = ws / "document.docx"
        convert_service.pdf_to_word(file.file, output)
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="document.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        background=background_tasks,
    )


@router.post("/markdown-to-pdf")
def markdown_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    if file is not None:
        if file.size is not None and file.size > MARKDOWN_MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux.")
        md_text = file.file.read().decode("utf-8", errors="ignore")
    else:
        md_text = text or ""
        if len(md_text) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Texte trop volumineux.")

    if not md_text.strip():
        raise HTTPException(status_code=400, detail="Contenu Markdown requis.")

    with job_workspace() as ws:
        output = ws / "document.pdf"
        convert_service.markdown_to_pdf(md_text, output)
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="document.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
