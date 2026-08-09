import json

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job
from app.services import forms as forms_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


@router.post("/inspect")
def inspect(file: UploadFile):
    _size_check(file)
    fields = forms_service.inspect_form(file.file)
    return JSONResponse(content={"fields": fields})


@router.post("/fill")
def fill(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    values: str = Form(...),
    flatten: bool = Form(False),
):
    _size_check(file)
    try:
        parsed_values = json.loads(values)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Format JSON invalide.") from exc

    ws = create_job_dir()
    try:
        output = ws / "filled.pdf"
        forms_service.fill_form(file.file, output, parsed_values, flatten)
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="filled.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
