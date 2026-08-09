import shutil

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pypdf import PdfReader

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job, get_job_dir, register_job
from app.schemas.organize import JobResponse, ReorderRequest
from app.services import organize as organize_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


@router.post("/merge")
def merge(files: list[UploadFile], background_tasks: BackgroundTasks):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Au moins deux PDF sont requis.")
    ws = create_job_dir()
    try:
        output = ws / "merged.pdf"
        ordered = []
        for upload in files:
            _size_check(upload)
            ordered.append((upload.filename or "file.pdf", upload.file))
        organize_service.merge_pdfs(ordered, output)
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="merged.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.post("/split")
def split(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    start: int | None = Form(None),
    end: int | None = Form(None),
    all_pages: bool = Form(False),
    every_n: int | None = Form(None),
):
    _size_check(file)
    ranges = None
    if every_n and every_n > 0:
        total_pages = len(PdfReader(file.file).pages)
        file.file.seek(0)
        ranges = [
            (i + 1, min(i + every_n, total_pages))
            for i in range(0, total_pages, every_n)
        ]
    elif not all_pages and (start is not None or end is not None):
        ranges = [(start or 1, end or 9999)]

    ws = create_job_dir()
    try:
        result_files = organize_service.split_pdf(file.file, ws, ranges)
        if len(result_files) == 1:
            out = result_files[0]
            background_tasks.add_task(delete_job, ws.name)
            return FileResponse(
                path=out,
                filename="split.pdf",
                media_type="application/pdf",
                background=background_tasks,
            )
        zip_path = ws / "split.zip"
        organize_service.build_zip(zip_path, result_files)
    except Exception:
        delete_job(ws.name)
        raise

    background_tasks.add_task(delete_job, ws.name)

    def iterfile():
        with open(zip_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=split.zip"},
        background=background_tasks,
    )


@router.post("/jobs", response_model=JobResponse)
def create_organize_job(file: UploadFile):
    _size_check(file)
    from app.core.tempfiles import create_job_dir

    ws = create_job_dir()
    input_path = ws / "input.pdf"
    with open(input_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    page_count = len(PdfReader(input_path).pages)
    thumbs = organize_service.generate_thumbnails(input_path, ws)
    job_id = ws.name
    register_job(ws)
    return JobResponse(job_id=job_id, page_count=page_count, thumbnails=thumbs)


@router.patch("/jobs/{job_id}")
def update_organize_job(job_id: str, request: ReorderRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    output_path = ws / "result.pdf"
    organize_service.reorder_and_delete_pages(
        input_path, output_path, request.new_order, request.rotations
    )
    return {"job_id": job_id, "status": "ready"}


@router.get("/jobs/{job_id}/download")
def download_organize_job(job_id: str, background_tasks: BackgroundTasks):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    output_path = ws / "result.pdf"
    if not output_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Aucun résultat prêt. Appliquez d'abord les modifications.",
        )
    background_tasks.add_task(delete_job, job_id)
    return FileResponse(
        path=output_path,
        filename="organized.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )


@router.delete("/jobs/{job_id}")
def abandon_organize_job(job_id: str):
    delete_job(job_id)
    return {"detail": "Job supprimé."}
