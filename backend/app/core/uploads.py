import magic
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.core.config import settings

PDF_MIME_TYPES = {"application/pdf"}
IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}

# Prevents a maliciously crafted or absurdly large PDF from exhausting
# CPU/memory during per-page processing (rendering, watermarking, etc.),
# independent of the file's byte size.
MAX_PDF_PAGES = 2000

_MAGIC_SNIFF_BYTES = 4096


def check_upload_size(file: UploadFile) -> None:
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


def _detect_mime(file: UploadFile) -> str:
    head = file.file.read(_MAGIC_SNIFF_BYTES)
    file.file.seek(0)
    return magic.from_buffer(head, mime=True)


def validate_pdf_upload(file: UploadFile, max_pages: int = MAX_PDF_PAGES) -> None:
    if _detect_mime(file) not in PDF_MIME_TYPES:
        raise HTTPException(
            status_code=400, detail="Le fichier fourni n'est pas un PDF valide."
        )
    try:
        page_count = len(PdfReader(file.file).pages)
    except FileNotDecryptedError:
        # Password-protected PDFs are a legitimate upload (e.g. /unlock) —
        # page count isn't readable without the password, so skip the cap
        # rather than reject a valid encrypted file.
        return
    except PdfReadError as exc:
        raise HTTPException(
            status_code=400, detail="Le fichier PDF est corrompu ou illisible."
        ) from exc
    finally:
        file.file.seek(0)
    if page_count > max_pages:
        raise HTTPException(
            status_code=400,
            detail=f"PDF trop volumineux : {page_count} pages (maximum {max_pages}).",
        )


def validate_image_upload(file: UploadFile) -> None:
    if _detect_mime(file) not in IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=400, detail="Le fichier fourni n'est pas une image valide."
        )
