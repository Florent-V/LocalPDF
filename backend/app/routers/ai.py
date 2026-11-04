import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from app.core.limiter import AI_RATE_LIMIT, limiter
from app.core.tempfiles import delete_job, get_job_dir, job_workspace, register_job
from app.core.uploads import check_upload_size, validate_pdf_upload
from app.schemas.ai import ChatRequest, SummarizeRequest, TranslateRequest
from app.services import ai as ai_service

router = APIRouter()


def _provider_or_raise(config):
    try:
        return ai_service.get_provider(config.provider, config.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pdf-to-markdown")
@limiter.limit(AI_RATE_LIMIT)
def pdf_to_markdown(
    request: Request, file: UploadFile, background_tasks: BackgroundTasks
):
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        md_text = ai_service.pdf_to_markdown(file.file)
        output = ws / "document.md"
        output.write_text(md_text, encoding="utf-8")
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="document.md",
        media_type="text/markdown",
        background=background_tasks,
    )


@router.post("/jobs")
@limiter.limit(AI_RATE_LIMIT)
def create_ai_job(request: Request, file: UploadFile):
    check_upload_size(file)
    validate_pdf_upload(file)
    with job_workspace() as ws:
        input_path = ws / "input.pdf"
        with open(input_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        with open(input_path, "rb") as f:
            md_text = ai_service.pdf_to_markdown(f)
        job_id = ws.name
        register_job(ws)
    return {"job_id": job_id, "markdown": md_text}


@router.post("/jobs/{job_id}/summarize")
@limiter.limit(AI_RATE_LIMIT)
async def summarize(request: Request, job_id: str, payload: SummarizeRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    with open(input_path, "rb") as f:
        md_text = ai_service.pdf_to_markdown(f)
    provider = _provider_or_raise(payload.config)
    result = await ai_service.summarize(provider, md_text, payload.language)
    return PlainTextResponse(content=result)


@router.post("/jobs/{job_id}/translate")
@limiter.limit(AI_RATE_LIMIT)
async def translate(request: Request, job_id: str, payload: TranslateRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    with open(input_path, "rb") as f:
        md_text = ai_service.pdf_to_markdown(f)
    provider = _provider_or_raise(payload.config)
    result = await ai_service.translate(provider, md_text, payload.target_language)
    return PlainTextResponse(content=result)


@router.post("/jobs/{job_id}/chat")
@limiter.limit(AI_RATE_LIMIT)
async def chat(request: Request, job_id: str, payload: ChatRequest):
    ws = get_job_dir(job_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Job introuvable ou expiré.")
    input_path = ws / "input.pdf"
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier source introuvable.")
    with open(input_path, "rb") as f:
        md_text = ai_service.pdf_to_markdown(f)
    provider = _provider_or_raise(payload.config)
    result = await ai_service.chat_with_pdf(provider, md_text, payload.question, [])
    return PlainTextResponse(content=result)


@router.delete("/jobs/{job_id}")
def abandon_ai_job(job_id: str):
    delete_job(job_id)
    return {"detail": "Job supprimé."}
