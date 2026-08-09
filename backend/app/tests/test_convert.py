import http.server
import io
import socketserver
import threading

from fastapi.testclient import TestClient

from app.main import app
from app.services import convert as convert_service

client = TestClient(app)


def test_markdown_to_pdf_creates_valid_pdf(tmp_path):
    output = tmp_path / "out.pdf"
    convert_service.markdown_to_pdf("# Title\n\nSome **bold** text.", output)
    assert output.exists()
    data = output.read_bytes()
    assert data.startswith(b"%PDF")


def test_markdown_to_pdf_from_text():
    response = client.post(
        "/api/v1/convert/markdown-to-pdf",
        data={"text": "# Titre\n\nTexte en **gras** et *italique*."},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_markdown_to_pdf_from_file():
    files = {"file": ("doc.md", io.BytesIO(b"# Titre\n\nContenu."), "text/markdown")}
    response = client.post("/api/v1/convert/markdown-to-pdf", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_markdown_to_pdf_empty_input():
    response = client.post("/api/v1/convert/markdown-to-pdf", data={"text": "   "})
    assert response.status_code == 400


def test_markdown_to_pdf_text_too_long():
    huge_text = "a" * (2 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/convert/markdown-to-pdf", data={"text": huge_text}
    )
    assert response.status_code == 413


def test_markdown_to_pdf_file_larger_than_2mb_accepted():
    # Create a markdown file larger than 2 MB but well under 200 MB limit
    large_text = "# Title\n\n" + ("a" * (3 * 1024 * 1024))  # 3 MB
    files = {"file": ("large.md", io.BytesIO(large_text.encode()), "text/markdown")}
    response = client.post("/api/v1/convert/markdown-to-pdf", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_markdown_to_pdf_file_larger_than_20mb_rejected():
    # 25 MB is above the dedicated 20 MB markdown cap, but well under the
    # shared 200 MB upload limit used elsewhere in the app.
    large_text = "a" * (25 * 1024 * 1024)
    files = {"file": ("huge.md", io.BytesIO(large_text.encode()), "text/markdown")}
    response = client.post("/api/v1/convert/markdown-to-pdf", files=files)
    assert response.status_code == 413
    assert response.json()["detail"] == "Fichier trop volumineux."


def test_markdown_to_pdf_blocks_external_resource_fetch(tmp_path):
    """xhtml2pdf must never perform network requests for markdown-embedded
    URLs (SSRF / local file read protection)."""
    hit_count = {"value": 0}

    class _CountingHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hit_count["value"] += 1
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(b"\x89PNG\r\n\x1a\n")

        def log_message(self, *args, **kwargs):  # silence test output
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _CountingHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        output = tmp_path / "ssrf.pdf"
        convert_service.markdown_to_pdf(
            f"![x](http://127.0.0.1:{port}/canary)", output
        )
    finally:
        httpd.shutdown()
        thread.join(timeout=5)

    assert hit_count["value"] == 0
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")
