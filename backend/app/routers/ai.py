import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job, get_job_dir, register_job
from app.schemas.ai import ChatRequest, SummarizeRequest, TranslateRequest
from app.services import ai as ai_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


def _provider_or_raise(config):
    try:
        return ai_service.get_provider(config.provider, config.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pdf-to-markdown")
def pdf_to_markdown(file: UploadFile, background_tasks: BackgroundTasks):
    _size_check(file)
    ws = create_job_dir()
    try:
        md_text = ai_service.pdf_to_markdown(file.file)
        output = ws / "document.md"
        output.write_text(md_text, encoding="utf-8")
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="document.md",
        media_type="text/markdown",
        background=background_tasks,
    )


@router.post("/jobs")
def create_ai_job(file: UploadFile):
    _size_check(file)
    ws = create_job_dir()
    input_path = ws / "input.pdf"
    with open(input_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    md_text = ai_service.pdf_to_markdown(open(input_path, "rb"))
    job_id = ws.name
    register_job(ws)
    return {"job_id": job_id, "markdown": md_text}


@router.post("/jobs/{job_id}/summarize")
async def summarize(job_id: str, request: SummarizeRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    md_text = ai_service.pdf_to_markdown(open(input_path, "rb"))
    provider = _provider_or_raise(request.config)
    result = await ai_service.summarize(provider, md_text, request.language)
    return PlainTextResponse(content=result)


@router.post("/jobs/{job_id}/translate")
async def translate(job_id: str, request: TranslateRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    md_text = ai_service.pdf_to_markdown(open(input_path, "rb"))
    provider = _provider_or_raise(request.config)
    result = await ai_service.translate(provider, md_text, request.target_language)
    return PlainTextResponse(content=result)


@router.post("/jobs/{job_id}/chat")
async def chat(job_id: str, request: ChatRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    md_text = ai_service.pdf_to_markdown(open(input_path, "rb"))
    provider = _provider_or_raise(request.config)
    result = await ai_service.chat_with_pdf(provider, md_text, request.question, [])
    return PlainTextResponse(content=result)


@router.delete("/jobs/{job_id}")
def abandon_ai_job(job_id: str):
    delete_job(job_id)
    return {"detail": "Job supprimé."}
