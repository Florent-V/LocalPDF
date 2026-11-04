from starlette.datastructures import Headers

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def needs_check(method: str, path: str) -> bool:
    """State-changing requests to the API and the logout. The back-channel
    logout is sent by the OAuth server (no browser, no Origin): not covered."""
    return method in UNSAFE_METHODS and (path.startswith("/api/") or path == "/auth/logout")


def is_allowed(headers: Headers, public_origin: str) -> bool:
    origin = headers.get("origin")
    if origin is not None:
        return origin == public_origin
    return headers.get("sec-fetch-site") == "same-origin"
