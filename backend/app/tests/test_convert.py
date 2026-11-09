import http.server
import io
import socketserver
import threading
from pathlib import Path

import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

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


def test_office_to_pdf_rejects_absolute_path_filename(tmp_path):
    """A filename that is an absolute path must never let office_to_pdf
    write outside output_dir. Path("a") / "/etc/passwd" collapses to
    "/etc/passwd" (pathlib absolute-path override), so an unsanitized
    original_name lets a client clobber an arbitrary file on disk."""
    output_dir = tmp_path / "job"
    output_dir.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("original content")

    try:
        convert_service.office_to_pdf(
            io.BytesIO(b"malicious overwrite\n"), output_dir, str(victim)
        )
    except Exception:
        pass

    assert victim.exists()
    assert victim.read_text() == "original content"


def test_office_to_pdf_rejects_relative_traversal_filename(tmp_path, monkeypatch):
    """A filename containing ".." must not let office_to_pdf escape
    output_dir when building the input path."""
    output_dir = tmp_path / "job"
    output_dir.mkdir()

    written_outside = []
    real_open = open

    def _spy_open(path, *args, **kwargs):
        resolved = Path(path).resolve()
        if resolved != output_dir.resolve() and output_dir.resolve() not in resolved.parents:
            written_outside.append(resolved)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _spy_open)

    try:
        convert_service.office_to_pdf(
            io.BytesIO(b"malicious\n"), output_dir, "../../escaped.txt"
        )
    except Exception:
        pass

    assert written_outside == []


def test_office_to_pdf_converts_normal_filename(tmp_path):
    """Regression guard: sanitizing original_name must not break a normal,
    well-behaved filename."""
    output_dir = tmp_path / "job"
    output_dir.mkdir()
    output = convert_service.office_to_pdf(
        io.BytesIO(b"Hello world\n"), output_dir, "notes.txt"
    )
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")


def test_office_to_pdf_does_not_leak_stderr_to_client(tmp_path, monkeypatch):
    """LibreOffice's raw stderr can contain internal file paths / container
    details; the client-facing error must be generic, not stderr echoed
    verbatim (services/convert.py previously did
    f"Erreur LibreOffice: {result.stderr...}")."""
    secret_marker = "INTERNAL-PATH-/app/secret-config-4f9c1e"

    class _FakeResult:
        returncode = 1
        stderr = secret_marker.encode()
        stdout = b""

    monkeypatch.setattr(
        convert_service.shutil, "which", lambda name: "/usr/bin/soffice"
    )
    monkeypatch.setattr(
        convert_service.subprocess, "run", lambda *a, **k: _FakeResult()
    )

    output_dir = tmp_path / "job"
    output_dir.mkdir()

    with pytest.raises(HTTPException) as exc_info:
        convert_service.office_to_pdf(
            io.BytesIO(b"hello\n"), output_dir, "notes.txt"
        )

    assert secret_marker not in exc_info.value.detail


def test_pdf_to_images_clamps_absurd_dpi(tmp_path):
    """An unbounded dpi lets a client force huge per-page pixmaps (CPU/
    memory DoS). dpi must be clamped to a sane maximum regardless of what
    the client requests."""
    pdf_stream = io.BytesIO()
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_stream)
    doc.close()
    pdf_stream.seek(0)

    paths = convert_service.pdf_to_images(pdf_stream, tmp_path, dpi=100_000, fmt="png")
    assert len(paths) == 1
    img = Image.open(paths[0])
    # At the clamped max (600 dpi) an A4 page is well under 8000px per side;
    # an unclamped 100000 dpi request would be orders of magnitude larger
    # (and in fact fails to allocate at all — see the RED run of this test).
    assert img.width < 8000
    assert img.height < 8000


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


def test_markdown_to_pdf_text_between_1mb_and_2mb_accepted():
    # Starlette caps text form fields at 1 MB by default; the route raises it.
    text = "# Title\n\n" + ("a" * (1536 * 1024))
    response = client.post("/api/v1/convert/markdown-to-pdf", data={"text": text})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
