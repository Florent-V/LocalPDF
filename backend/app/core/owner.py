from fastapi import Depends

from app.auth.deps import AuthUser, current_user
from app.core.tempfiles import current_owner


async def bind_owner(user: AuthUser = Depends(current_user)) -> None:
    """Router-level dependency: scopes the request's jobs to the logged-in user.

    Async on purpose: it runs in the request's own context, so the
    `current_owner` it sets is visible to the (threadpool) endpoint and its
    background tasks.
    """
    current_owner.set(user.sub)
