from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_oversized_content_length_rejected_before_body_is_read():
    """Content-Length declared above the global upload ceiling must be
    rejected at the ASGI layer, before Starlette buffers/parses the body —
    unlike the per-route `check_upload_size`, which only runs after the
    full multipart body has already been parsed into memory/disk."""
    huge = b"x" * 10
    headers = {"content-length": str(300 * 1024 * 1024)}  # 300MB > 200MB default
    response = client.post(
        "/api/v1/organize/merge",
        content=huge,
        headers=headers,
    )
    assert response.status_code == 413


def test_normal_sized_request_still_works():
    response = client.get("/api/health")
    assert response.status_code == 200
