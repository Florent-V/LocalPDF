import json

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.tempfiles import delete_job, job_workspace
from app.core.uploads import check_upload_size, validate_pdf_upload
from app.services import forms as forms_service

router = APIRouter()


@router.post("/inspect")
def inspect(file: UploadFile):
    check_upload_size(file)
    validate_pdf_upload(file)
    fields = forms_service.inspect_form(file.file)
    return JSONResponse(content={"fields": fields})


@router.post("/fill")
def fill(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    values: str = Form(...),
    flatten: bool = Form(False),
):
    check_upload_size(file)
    validate_pdf_upload(file)
    try:
        parsed_values = json.loads(values)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Format JSON invalide.") from exc

    with job_workspace() as ws:
        output = ws / "filled.pdf"
        forms_service.fill_form(file.file, output, parsed_values, flatten)
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="filled.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
