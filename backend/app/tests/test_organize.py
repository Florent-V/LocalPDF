import io

import fitz
import pytest
from fastapi.testclient import TestClient

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
    return stream.read()


@pytest.fixture
def sample_pdf():
    return _make_pdf(3)


def test_merge_pdfs(sample_pdf):
    files = [
        ("files", ("file1.pdf", io.BytesIO(sample_pdf), "application/pdf")),
        ("files", ("file2.pdf", io.BytesIO(sample_pdf), "application/pdf")),
    ]
    response = client.post("/api/v1/organize/merge", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_split_pdf(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post(
        "/api/v1/organize/split", files=files, data={"all_pages": "true"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_split_pdf_every_n():
    import zipfile

    from pypdf import PdfReader

    sample = _make_pdf(5)
    files = {"file": ("doc.pdf", io.BytesIO(sample), "application/pdf")}
    response = client.post(
        "/api/v1/organize/split", files=files, data={"every_n": "2"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = sorted(zf.namelist())
    assert len(names) == 3
    page_counts = [len(PdfReader(io.BytesIO(zf.read(name))).pages) for name in names]
    assert page_counts == [2, 2, 1]


def test_organize_job(sample_pdf):
    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post("/api/v1/organize/jobs", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["page_count"] == 3
    assert len(data["thumbnails"]) == 3

    job_id = data["job_id"]
    response = client.patch(
        f"/api/v1/organize/jobs/{job_id}",
        json={"new_order": [3, 1]},
    )
    assert response.status_code == 200

    response = client.get(f"/api/v1/organize/jobs/{job_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_organize_job_reorder_and_rotate(sample_pdf):
    from pypdf import PdfReader

    files = {"file": ("doc.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = client.post("/api/v1/organize/jobs", files=files)
    job_id = response.json()["job_id"]

    response = client.patch(
        f"/api/v1/organize/jobs/{job_id}",
        json={"new_order": [3, 1], "rotations": {"1": 90, "3": 180}},
    )
    assert response.status_code == 200

    response = client.get(f"/api/v1/organize/jobs/{job_id}/download")
    assert response.status_code == 200

    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 2
    # new_order [3, 1]: first output page is original page 3 (rotated 180),
    # second output page is original page 1 (rotated 90).
    assert reader.pages[0].rotation == 180
    assert reader.pages[1].rotation == 90
