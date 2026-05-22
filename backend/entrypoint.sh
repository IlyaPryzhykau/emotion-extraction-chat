#!/usr/bin/env sh
# Apply pending migrations before serving, so the schema is always current.
# `alembic upgrade head` is idempotent — a no-op when already up to date.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
# Honour a command passed by compose (dev override adds --reload); otherwise
# fall back to the default production command.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
