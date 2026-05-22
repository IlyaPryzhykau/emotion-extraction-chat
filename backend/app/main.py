"""FastAPI application entrypoint.

The database schema is managed by Alembic migrations (``alembic upgrade head``,
run at container start), not by the app, so startup performs no DDL.
"""

from fastapi import FastAPI

app = FastAPI(title="Conversational Emotion Extraction")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe used by the proxy and for quick manual checks."""
    return {"status": "ok"}
