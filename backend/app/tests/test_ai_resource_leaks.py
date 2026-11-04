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
def ai_job_id():
    files = {"file": ("doc.pdf", io.BytesIO(_make_pdf()), "application/pdf")}
    response = client.post("/api/v1/ai/jobs", files=files)
    assert response.status_code == 200
    return response.json()["job_id"]


class _OpenSpy:
    """Wraps builtins.open to record every returned file object so a test
    can assert they were all closed once the request finished."""

    def __init__(self, monkeypatch):
        self.opened: list = []
        real_open = open
        monkeypatch.setattr("builtins.open", self._spy)
        self._real_open = real_open

    def _spy(self, *args, **kwargs):
        f = self._real_open(*args, **kwargs)
        self.opened.append(f)
        return f


@pytest.fixture
def open_spy(monkeypatch):
    return _OpenSpy(monkeypatch)


def test_summarize_closes_input_file_handle(ai_job_id, open_spy):
    client.post(
        f"/api/v1/ai/jobs/{ai_job_id}/summarize",
        json={
            "config": {"provider": "ollama", "base_url": "http://127.0.0.1:1", "model": "x"},
            "language": "fr",
        },
    )
    assert open_spy.opened, "expected at least one file to be opened"
    assert all(f.closed for f in open_spy.opened), "input.pdf handle was left open"


def test_translate_closes_input_file_handle(ai_job_id, open_spy):
    client.post(
        f"/api/v1/ai/jobs/{ai_job_id}/translate",
        json={
            "config": {"provider": "ollama", "base_url": "http://127.0.0.1:1", "model": "x"},
            "target_language": "en",
        },
    )
    assert open_spy.opened, "expected at least one file to be opened"
    assert all(f.closed for f in open_spy.opened), "input.pdf handle was left open"


def test_chat_closes_input_file_handle(ai_job_id, open_spy):
    client.post(
        f"/api/v1/ai/jobs/{ai_job_id}/chat",
        json={
            "config": {"provider": "ollama", "base_url": "http://127.0.0.1:1", "model": "x"},
            "question": "What is this document about?",
        },
    )
    assert open_spy.opened, "expected at least one file to be opened"
    assert all(f.closed for f in open_spy.opened), "input.pdf handle was left open"


def test_create_ai_job_closes_input_file_handle(open_spy):
    files = {"file": ("doc.pdf", io.BytesIO(_make_pdf()), "application/pdf")}
    response = client.post("/api/v1/ai/jobs", files=files)
    assert response.status_code == 200
    assert open_spy.opened, "expected at least one file to be opened"
    assert all(f.closed for f in open_spy.opened), "input.pdf handle was left open"
