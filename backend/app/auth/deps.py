from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthUser:
    sub: str
    name: str | None = None
    email: str | None = None
    roles: tuple[str, ...] = ()


async def current_user(request: Request) -> AuthUser:
    """The user the middleware authenticated; the middleware already answered
    401 for protected paths, this guards a route outside the protected prefixes."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user
