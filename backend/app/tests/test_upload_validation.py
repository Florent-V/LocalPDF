import io

import fitz
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image

from app.core.uploads import (
    MAX_PDF_PAGES,
    check_upload_size,
    validate_image_upload,
    validate_pdf_upload,
)
from app.main import app

client = TestClient(app)


def _make_pdf(num_pages: int = 1):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    stream.seek(0)
    return stream


def _make_image_bytes(fmt: str = "PNG"):
    img = Image.new("RGB", (10, 10), color="red")
    stream = io.BytesIO()
    img.save(stream, format=fmt)
    stream.seek(0)
    return stream


class _FakeUploadFile:
    """Minimal stand-in exposing the .file attribute validate_* reads."""

    def __init__(self, stream):
        self.file = stream


def test_validate_pdf_upload_accepts_real_pdf():
    validate_pdf_upload(_FakeUploadFile(_make_pdf()))  # must not raise


def test_validate_pdf_upload_rewinds_stream():
    stream = _make_pdf()
    validate_pdf_upload(_FakeUploadFile(stream))
    assert stream.tell() == 0


def test_validate_pdf_upload_rejects_png_disguised_as_pdf():
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(_FakeUploadFile(_make_image_bytes("PNG")))
    assert exc_info.value.status_code == 400


def test_validate_pdf_upload_rejects_plain_text():
    stream = io.BytesIO(b"just some plain text, not a pdf at all")
    with pytest.raises(HTTPException):
        validate_pdf_upload(_FakeUploadFile(stream))


def test_validate_pdf_upload_rejects_pdf_over_page_limit():
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(_FakeUploadFile(_make_pdf(MAX_PDF_PAGES + 1)))
    assert exc_info.value.status_code == 400


def test_validate_pdf_upload_accepts_password_protected_pdf(tmp_path):
    """A password-protected PDF is a legitimate upload for /unlock — page
    count can't be read without the password, so it must not be rejected
    as corrupted."""
    from app.services import security as security_service

    output = tmp_path / "protected.pdf"
    security_service.protect_pdf(_make_pdf(), output, "secret123", None, True, False)
    with open(output, "rb") as f:
        validate_pdf_upload(_FakeUploadFile(f))  # must not raise


def test_validate_image_upload_accepts_real_png():
    validate_image_upload(_FakeUploadFile(_make_image_bytes("PNG")))  # must not raise


def test_validate_image_upload_accepts_real_jpeg():
    validate_image_upload(_FakeUploadFile(_make_image_bytes("JPEG")))  # must not raise


def test_validate_image_upload_rejects_pdf_disguised_as_image():
    with pytest.raises(HTTPException) as exc_info:
        validate_image_upload(_FakeUploadFile(_make_pdf()))
    assert exc_info.value.status_code == 400


def test_check_upload_size_rejects_file_over_limit():
    upload = UploadFile(filename="big.pdf", file=io.BytesIO(b"x"))
    upload.size = 999_999_999_999
    with pytest.raises(HTTPException) as exc_info:
        check_upload_size(upload)
    assert exc_info.value.status_code == 413


def test_check_upload_size_accepts_file_under_limit():
    upload = UploadFile(filename="small.pdf", file=io.BytesIO(b"x"))
    upload.size = 100
    check_upload_size(upload)  # must not raise


def test_check_upload_size_accepts_unknown_size():
    upload = UploadFile(filename="unknown.pdf", file=io.BytesIO(b"x"))
    upload.size = None
    check_upload_size(upload)  # must not raise


def test_merge_endpoint_rejects_non_pdf_upload():
    files = [
        ("files", ("a.pdf", _make_pdf(), "application/pdf")),
        ("files", ("b.pdf", io.BytesIO(b"not a real pdf"), "application/pdf")),
    ]
    response = client.post("/api/v1/organize/merge", files=files)
    assert response.status_code == 400


def test_images_to_pdf_endpoint_rejects_non_image_upload():
    files = [
        ("files", ("img1.png", _make_image_bytes("PNG"), "image/png")),
        ("files", ("evil.png", io.BytesIO(b"not an image"), "image/png")),
    ]
    response = client.post("/api/v1/convert/images-to-pdf", files=files)
    assert response.status_code == 400
