"""Password hashing and signed session tokens.

Pure functions with no FastAPI or database coupling, so they are trivially
testable. Passwords use bcrypt; the session cookie is a signed, expiring token
(``itsdangerous``) carrying only the user id — there is no server-side session
store.
"""

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

# Name of the cookie that carries the signed session token.
SESSION_COOKIE = "session"

# The salt namespaces this signature to session cookies; it is not a password
# salt (bcrypt salts each hash itself).
_serializer = URLSafeTimedSerializer(settings.session_secret, salt="session")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of ``plain``, safe to store as text.

    bcrypt only considers the first 72 bytes of the input; that is standard
    bcrypt behaviour and acceptable here.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the stored bcrypt ``hashed`` value."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def issue_session_token(user_id: str) -> str:
    """Create a signed, timestamped session token for ``user_id``."""
    return _serializer.dumps(user_id)


def read_session_token(token: str) -> str | None:
    """Return the user id from a valid token, or None if invalid/expired.

    Never raises on bad input: a tampered, malformed, or expired token simply
    yields None so callers treat it as "not authenticated".
    """
    try:
        user_id = _serializer.loads(token, max_age=settings.session_max_age)
    except (BadSignature, SignatureExpired):
        return None
    return user_id if isinstance(user_id, str) else None
