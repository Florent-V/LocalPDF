import os
import tempfile

# The app builds its auth settings at import: give it a complete, harmless
# environment before anything imports app.main.
os.environ.setdefault("OAUTH_ISSUER", "https://auth.test")
os.environ.setdefault("OAUTH_CLIENT_ID", "localpdf-test")
os.environ.setdefault("OAUTH_CLIENT_SECRET", "test-secret")
os.environ.setdefault("PUBLIC_ORIGIN", "http://localhost:3010")
os.environ.setdefault("SESSION_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="localpdf-tests-"), "sessions.db"))
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest  # noqa: E402

from app.auth import csrf  # noqa: E402
from app.auth.deps import AuthUser  # noqa: E402
from app.core.limiter import limiter  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """All test files share the same TestClient key ("testclient" — there's
    no real client IP under TestClient), so without a reset between tests
    the global rate limit accumulates across the whole suite and start
    failing tests unrelated to rate limiting, depending on run order."""
    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def _logged_in(request, monkeypatch):
    """Outside tests/auth, the suite runs as an already-authenticated user:
    the session cookie value *is* the user ("alice" → user alice), "test-user"
    when there is no cookie. The session machinery itself is covered by tests/auth."""
    if ".auth." in request.module.__name__:
        yield
        return
    from app.main import auth

    async def fake_authenticate(ctx, session_id):
        return AuthUser(sub=session_id or "test-user", name="Test", email="test@example.com")

    monkeypatch.setattr("app.auth.middleware.authenticate", fake_authenticate)
    monkeypatch.setattr(csrf, "needs_check", lambda method, path: False)
    monkeypatch.setattr(auth.discovery, "metadata", {"issuer": auth.settings.oauth_issuer})
    yield
