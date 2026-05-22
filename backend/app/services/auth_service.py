"""Auth business logic: account creation and credential checks.

Routers stay thin and call into here; this module owns the DB access and the
password hashing/verification (via ``core.security``).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User


class EmailAlreadyExists(Exception):
    """Raised when signing up with an email that is already registered."""


def create_user(db: Session, email: str, password: str) -> User:
    """Create and persist a new user.

    Args:
        db: Active database session.
        email: Already-normalized email (the schema lowercases/trims it).
        password: Plaintext password; stored only as a bcrypt hash.

    Returns:
        The created user.

    Raises:
        EmailAlreadyExists: if the email is already taken. We check first for a
            friendly error, but also catch the unique-constraint violation so a
            concurrent signup can't slip through the check.
    """
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise EmailAlreadyExists(email)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyExists(email) from exc
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if the email/password are valid, else None."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
