"""Shared FastAPI dependencies.

``get_current_user`` resolves the authenticated user from the signed session
cookie and is the single guard protected routes depend on.
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import SESSION_COOKIE, read_session_token
from app.db.base import get_db
from app.db.models import User

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Return the logged-in user, or raise 401.

    Every failure mode (no cookie, bad/expired token, deleted user) yields the
    same 401 so the response never reveals which step failed.
    """
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_session_token(token) if token else None
    if user_id is None:
        raise _UNAUTHENTICATED
    try:
        pk = uuid.UUID(user_id)
    except ValueError:
        raise _UNAUTHENTICATED
    user = db.get(User, pk)
    if user is None:
        raise _UNAUTHENTICATED
    return user
