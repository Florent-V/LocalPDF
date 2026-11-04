from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Rejects requests whose declared Content-Length exceeds max_bytes
    before Starlette buffers/parses the body — unlike a per-route check on
    `UploadFile.size`, which only runs after the full multipart body has
    already been read into memory/disk.

    This only catches well-behaved clients that declare Content-Length (the
    normal case for browser/curl form uploads); it does not defend against
    a chunked-transfer client that lies about size, which would need a
    streaming byte-counter at the reverse-proxy layer instead.
    """

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            content_length = Headers(scope=scope).get("content-length")
            if content_length is not None and int(content_length) > self.max_bytes:
                response = JSONResponse(
                    {"detail": "Corps de requête trop volumineux."},
                    status_code=413,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
