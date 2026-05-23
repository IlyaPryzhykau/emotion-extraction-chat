# Conversational Emotion Extraction

A web app that talks with you about your day in English, then extracts the
negative emotions from the conversation into a structured, evidence-grounded
report.

**Framing (the core judgment call).** The app serves two parties whose interests
pull apart: the person wants to be heard; the business wants structured negative
emotions. We treat extraction as a *silent byproduct of a conversation worth
having on its own* — the conversationalist is a warm listener that never hunts for
negativity, and a separate analyst pass turns the transcript into the report. See
`ASSUMPTIONS.md` for the decisions made under ambiguity.

> Built as a 2-day case study. This README grows with the code; sections marked
> _(coming)_ are not built yet, and we keep it honest about that.

## Status

- [x] Backend foundation — config, DB models, emotion taxonomy
- [x] UUID keys + Alembic migrations
- [x] Dockerized dev/prod stacks (db + app)
- [x] Auth (signup/login/logout, session cookie) + tests
- [x] Chat: conversations + streaming (SSE) conversationalist + tests
- [x] End-of-session analysis: structured grounded emotion extraction + tests
- [ ] Evaluation harness
- [ ] Frontend (login / chat / report / history)
- [ ] Public deployment

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **DB:** PostgreSQL (dedicated `emotion_extraction_chat` schema), Alembic migrations
- **LLM:** OpenAI — a fast/cheap model for the conversation, a strong model once per
  session for the analysis (IDs are configurable via env)
- **Frontend:** React + TypeScript (Vite) _(coming)_
- **Infra:** Docker Compose; Caddy + frontend on a Hetzner VPS _(coming)_

## Repo layout

```
backend/      FastAPI app, SQLAlchemy models, Alembic migrations, eval harness
deploy/       docker-compose.yml (dev) + docker-compose.prod.yml
frontend/     React + TypeScript (coming)
```

## Running locally

**Prerequisites:** Docker Desktop running; a `backend/.env` file.

```bash
cd backend && cp .env.example .env   # then fill in OPENAI_API_KEY
```

**Dev (hot reload)** — from `deploy/`:

```bash
docker compose up --build
```

Source is bind-mounted and uvicorn runs with `--reload`, so code changes apply
without a rebuild. Migrations run automatically at startup.

**Prod-like (code baked into the image)** — from `deploy/`:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The dev and prod stacks are two independent, self-contained files (no overlay), so
the prod run can never accidentally pick up dev settings.

**Check it's up:**

```bash
curl http://localhost:8000/api/health     # -> {"status":"ok"}
```

**Inspect the database** (dev only) — Postgres is published on host port **5439**:

| Field | Value |
|-------|-------|
| Host / Port | `localhost` / `5439` |
| Database | `emotions` |
| User / Password | `postgres` / `postgres` |
| Schema | `emotion_extraction_chat` |

## Configuration

All config comes from the environment (see `backend/.env.example`):

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string |
| `DB_SCHEMA` | Schema that owns all app tables/enums |
| `OPENAI_API_KEY` | OpenAI key |
| `CHAT_MODEL` | Fast model for the conversation |
| `EXTRACTION_MODEL` | Strong model for the end-of-session analysis |
| `SESSION_SECRET` | Signs the session cookie |

Tip: `python scripts/list_models.py` lists the model IDs your key can actually use.

## Database & migrations

- All tables/enums live in the `emotion_extraction_chat` schema, not `public`.
- Primary keys are app-generated **UUIDv4** (native Postgres `UUID`).
- Schema is managed by **Alembic**, not by the app. `alembic upgrade head` runs at
  container start (see `backend/entrypoint.sh`); the app itself does no DDL.

```bash
# from backend/ (with a reachable DATABASE_URL)
alembic upgrade head            # apply migrations
alembic revision --autogenerate -m "message"   # create a new migration
```

## Tests

Backend tests use pytest against a real Postgres (each test runs in a transaction
that is rolled back, so nothing persists). With the dev stack running:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The test DB defaults to the dev Postgres on `localhost:5439`; override with
`TEST_DATABASE_URL` if needed.

## Evaluation

_(coming)_ A small harness checks that every extracted emotion's evidence quote
appears verbatim in the transcript, plus label precision/recall on hand-written
fixtures.

## Deployment

_(coming)_ Public HTTPS URL on a Hetzner VPS (Caddy + `sslip.io`).

## Assumptions & "with another week"

Decisions made under ambiguity, and what we'd do with more time, are documented in
`ASSUMPTIONS.md`.
