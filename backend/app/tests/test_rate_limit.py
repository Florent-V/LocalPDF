import io

import fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_exceeding_global_rate_limit_returns_429():
    statuses = [client.get("/api/health").status_code for _ in range(65)]
    assert 429 in statuses


def test_requests_within_limit_all_succeed():
    statuses = [client.get("/api/health").status_code for _ in range(10)]
    assert all(s == 200 for s in statuses)


def test_ai_endpoints_use_a_tighter_rate_limit():
    """AI calls can cost real provider money — they must be capped well
    below the generous global default so a script can't rack up cost."""
    doc = fitz.open()
    doc.new_page()
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    pdf_bytes = stream.getvalue()

    statuses = []
    for _ in range(25):
        files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        statuses.append(client.post("/api/v1/ai/jobs", files=files).status_code)

    assert 429 in statuses
    assert statuses.count(429) < len(statuses)
