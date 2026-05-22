"""FastAPI application entrypoint.

Wires routers and creates database tables on startup. We use
``Base.metadata.create_all`` rather than a migration tool: for a 2-day case study
with a fresh database this is the simplest correct thing; a real deployment would
use Alembic (a "with another week" item).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.schema import CreateSchema

from app.core.config import settings
from app.db.base import Base, engine

# Importing models registers them on ``Base.metadata`` so create_all sees them.
from app.db import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ensure the app schema and tables exist on startup.

    Idempotent: the schema is created if missing, and create_all only creates
    tables that do not yet exist.
    """
    with engine.begin() as conn:
        conn.execute(CreateSchema(settings.db_schema, if_not_exists=True))
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Conversational Emotion Extraction", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe used by the proxy and for quick manual checks."""
    return {"status": "ok"}
