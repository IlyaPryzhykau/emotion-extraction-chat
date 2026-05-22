"""Auth API: signup, login, logout, and the current-user endpoint.

Thin router: validation lives in the schemas, logic in ``auth_service``, and the
session cookie is set/cleared here.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, SignupRequest, UserOut
from app.core.config import settings
from app.core.security import SESSION_COOKIE, issue_session_token
from app.db.base import get_db
from app.db.models import User
from app.services.auth_service import EmailAlreadyExists, authenticate, create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User) -> None:
    """Attach a signed, httpOnly session cookie identifying ``user``."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session_token(str(user.id)),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    """Create an account and log the new user in."""
    try:
        user = create_user(db, payload.email, payload.password)
    except EmailAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    _set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    """Authenticate and start a session."""
    user = authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    _set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return user
