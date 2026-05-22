# Backend image: FastAPI app + Alembic migrations.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first so the layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Runs migrations, then starts the API (see entrypoint.sh).
ENTRYPOINT ["sh", "./entrypoint.sh"]
