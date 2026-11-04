from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """Per-user key (set by the auth middleware), so users behind the same
    proxy IP do not share a bucket. Falls back to the IP for unauthenticated
    requests (/api/health, 401s)."""
    user = getattr(request.state, "user", None)
    return f"user:{user.sub}" if user else get_remote_address(request)


# Per-user request cap. Generous enough for normal usage while stopping a
# scripted flood from exhausting CPU/disk on PDF processing or racking up
# AI-provider cost.
limiter = Limiter(key_func=_rate_limit_key, default_limits=["60/minute"])

# Tighter cap for AI endpoints: each call can incur real provider cost.
AI_RATE_LIMIT = "20/minute"
