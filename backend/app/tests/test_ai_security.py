import http.server
import io
import socketserver
import threading

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.providers.ollama_provider import OllamaProvider

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


def test_ollama_provider_rejects_link_local_metadata_url():
    """169.254.169.254 is the cloud metadata endpoint on AWS/GCP/Azure —
    a client must not be able to make the server fetch it via a
    user-supplied Ollama base_url (SSRF)."""
    with pytest.raises(ValueError):
        OllamaProvider(base_url="http://169.254.169.254/latest/meta-data/", model="llama3.1:8b")


def test_ollama_provider_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        OllamaProvider(base_url="file:///etc/passwd", model="llama3.1:8b")


def test_ollama_provider_rejects_malformed_url():
    with pytest.raises(ValueError):
        OllamaProvider(base_url="not-a-url", model="llama3.1:8b")


def test_ollama_provider_allows_localhost():
    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1:8b")
    assert provider.base_url == "http://localhost:11434"


def test_ollama_provider_allows_loopback_ip():
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="llama3.1:8b")
    assert provider.base_url == "http://127.0.0.1:11434"


def test_ollama_provider_allows_lan_address():
    """The BYO-Ollama-URL feature is meant to support a self-hosted Ollama
    on the user's own LAN — private-range addresses must stay allowed."""
    provider = OllamaProvider(base_url="http://192.168.1.50:11434", model="llama3.1:8b")
    assert provider.base_url == "http://192.168.1.50:11434"


def test_create_ai_job_succeeds(ai_job_id):
    """Regression guard for app/services/ai/__init__.py re-exports: job
    creation must not 500 with AttributeError."""
    assert ai_job_id


def test_summarize_does_not_leak_upstream_response_body(ai_job_id):
    """A real Ollama-shaped server that errors must not have its raw
    response body echoed back to the client — that body could reveal
    internal service details useful for enumerating the internal
    network (services/ai/providers/ollama_provider.py:33 today does
    `detail=f"Erreur Ollama : {exc.response.text}"`)."""
    secret_marker = "INTERNAL-TRACE-4f9c1e-do-not-leak"

    class _FailingOllamaHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(secret_marker.encode())

        def log_message(self, *args, **kwargs):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _FailingOllamaHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        response = client.post(
            f"/api/v1/ai/jobs/{ai_job_id}/summarize",
            json={
                "config": {
                    "provider": "ollama",
                    "base_url": f"http://127.0.0.1:{port}",
                    "model": "llama3.1:8b",
                },
                "language": "fr",
            },
        )
    finally:
        httpd.shutdown()
        thread.join(timeout=5)

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert secret_marker not in detail
