import io

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

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


def _make_image(fmt: str = "PNG"):
    img = Image.new("RGB", (100, 100), color="red")
    stream = io.BytesIO()
    img.save(stream, format=fmt)
    stream.seek(0)
    return stream.read()


def test_images_to_pdf():
    img_bytes = _make_image()
    files = [
        ("files", ("img1.png", io.BytesIO(img_bytes), "image/png")),
        ("files", ("img2.png", io.BytesIO(img_bytes), "image/png")),
    ]
    response = client.post("/api/v1/convert/images-to-pdf", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_pdf_to_images(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post(
        "/api/v1/convert/pdf-to-images",
        files=files,
        data={"dpi": "72", "fmt": "png"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_pdf_to_word(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post("/api/v1/convert/pdf-to-word", files=files)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
