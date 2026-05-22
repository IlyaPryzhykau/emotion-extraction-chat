"""Database engine, session factory, and declarative base.

We use SQLAlchemy 2.0 typed style (``Mapped`` / ``mapped_column``) throughout.
A FastAPI dependency (``get_db``) yields a request-scoped session.
"""

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# ``pool_pre_ping`` avoids handing out connections that the database has already
# dropped (common with managed Postgres that closes idle connections).
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

# expire_on_commit=False keeps ORM objects readable after commit, so endpoints can
# return a just-saved row without triggering a second SELECT.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    All tables and ENUM types are bound to ``settings.db_schema`` so the app owns a
    dedicated Postgres schema instead of sharing ``public``.
    """

    metadata = MetaData(schema=settings.db_schema)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session, closing it afterwards.

    Used as a FastAPI dependency so each request gets its own session and the
    connection is always returned to the pool.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
