import io

import fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
# Outside tests/auth the session cookie value is the logged-in user (see conftest).
ALICE = {"Cookie": "session=alice"}
BOB = {"Cookie": "session=bob"}


def _pdf_upload():
    doc = fitz.open()
    doc.new_page()
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    return {"file": ("doc.pdf", io.BytesIO(stream.getvalue()), "application/pdf")}


def test_health_is_ready_once_the_oauth_metadata_is_known():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_health_is_503_until_the_oauth_metadata_is_known(monkeypatch):
    from app.main import auth

    monkeypatch.setattr(auth.discovery, "metadata", None)
    assert client.get("/api/health").status_code == 503


def test_jobs_are_private_to_their_owner():
    job_id = client.post("/api/v1/organize/jobs", files=_pdf_upload(), headers=ALICE).json()["job_id"]

    patch = {"new_order": [1]}
    assert client.patch(f"/api/v1/organize/jobs/{job_id}", json=patch, headers=BOB).status_code == 404
    client.delete(f"/api/v1/organize/jobs/{job_id}", headers=BOB)

    assert client.patch(f"/api/v1/organize/jobs/{job_id}", json=patch, headers=ALICE).status_code == 200
    assert client.get(f"/api/v1/organize/jobs/{job_id}/download", headers=ALICE).status_code == 200


def test_rate_limit_is_per_user_not_per_ip():
    """Behind the reverse proxy every request has the same client IP: one user
    hitting the limit must not block the others."""
    statuses = [client.post("/api/v1/ai/jobs", files=_pdf_upload(), headers=ALICE).status_code for _ in range(25)]
    assert 429 in statuses
    assert client.post("/api/v1/ai/jobs", files=_pdf_upload(), headers=BOB).status_code == 200
