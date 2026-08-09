import io

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_pdf(text: str = "Hello"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    return stream.getvalue()


@pytest.fixture
def sample_pdf():
    return _make_pdf("Hello")


def test_rotate(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post("/api/v1/modify/rotate", files=files, data={"angle": "90"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def _make_multi_page_pdf(pages: int = 3):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    return stream.getvalue()


def test_rotate_with_per_page_map():
    pdf_bytes = _make_multi_page_pdf(3)
    files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/modify/rotate",
        files=files,
        data={"angle": "90", "rotations": '{"1": 90, "2": 180}'},
    )
    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert result_doc[0].rotation == 90
    assert result_doc[1].rotation == 180
    assert result_doc[2].rotation == 0
    result_doc.close()


def test_rotate_with_invalid_rotations_json():
    pdf_bytes = _make_multi_page_pdf(1)
    files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/modify/rotate",
        files=files,
        data={"angle": "90", "rotations": "not-json"},
    )
    assert response.status_code == 400


def test_watermark_text(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post(
        "/api/v1/modify/watermark",
        files=files,
        data={"text": "Confidentiel", "opacity": "0.5"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_protect_and_unlock(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post(
        "/api/v1/security/protect",
        files=files,
        data={"user_password": "secret"},
    )
    assert response.status_code == 200
    protected = io.BytesIO(response.content)

    files = {"file": ("doc.pdf", protected, "application/pdf")}
    response = client.post(
        "/api/v1/security/unlock", files=files, data={"password": "secret"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_unlock_wrong_password(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post(
        "/api/v1/security/protect",
        files=files,
        data={"user_password": "secret"},
    )
    protected = io.BytesIO(response.content)

    files = {"file": ("doc.pdf", protected, "application/pdf")}
    response = client.post(
        "/api/v1/security/unlock", files=files, data={"password": "wrong"}
    )
    assert response.status_code == 422
