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
- [x] Evaluation harness (grounding check + label precision/recall on fixtures)
- [x] Frontend (login / chat / report / history)
- [x] Public deployment (Docker Compose on a cloud VM, HTTPS via sslip.io)

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **DB:** PostgreSQL (dedicated `emotion_extraction_chat` schema), Alembic migrations
- **LLM:** OpenAI — a fast/cheap model for the conversation, a strong model once per
  session for the analysis (IDs are configurable via env)
- **Frontend:** React + TypeScript (Vite)
- **Infra:** Docker Compose; in prod, Caddy serves the built frontend and proxies
  the API, with HTTPS via `sslip.io` on a Hetzner VPS

## Repo layout

```
backend/      FastAPI app, SQLAlchemy models, Alembic migrations, eval harness
deploy/       docker-compose.yml (dev) + docker-compose.prod.yml + Caddy
frontend/     React + TypeScript (Vite) single-page app
```

## Architecture

```
                  ┌────────────────────────────────────────────┐
   browser ──────►│ Caddy (HTTPS via Let's Encrypt + sslip.io)  │
                  │   • serves the built React SPA              │
                  │   • reverse-proxies /api/* (SSE-friendly) ──┼──► FastAPI (app)
                  └─────────────────────────────────────────────┘        │
                                                                          ├─► Postgres
                                                                          └─► OpenAI
```

**Two separated LLM roles** are the heart of the system:

- **Conversationalist** (cheap model, streamed): a warm listener that helps you talk
  through your day. It is *never* told the app extracts emotions — no hunting, no
  labelling, no clinical framing. Grounded in reflective listening / motivational
  interviewing / the Day Reconstruction Method.
- **Analyst** (strong model, once on "End & analyze"): reads the full raw transcript
  and returns structured negative-emotion findings — label (fixed taxonomy),
  intensity, trigger, a **verbatim evidence quote**, and confidence. Conservative
  (an empty result is valid), with a confidence floor.

Emotion extraction is a *silent byproduct* of a conversation worth having on its
own; nothing about emotions is shown during the chat.

## Running locally

**Prerequisites:** Docker Desktop running; a `backend/.env` file.

```bash
cd backend && cp .env.example .env   # then fill in OPENAI_API_KEY
```

**Dev (hot reload)** — from `deploy/`:

```bash
docker compose up --build
```

This brings up the whole stack: the **frontend at http://localhost:5173**, the API
at http://localhost:8000, and Postgres on 5439. Both frontend and backend source
are bind-mounted with hot reload, so code changes apply without a rebuild.
Migrations run automatically at startup.

**Prod-like (code baked into the images)** — from `deploy/`:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Here Caddy serves the built frontend and proxies `/api` to the backend on one
origin (http://localhost). The dev and prod stacks are two independent,
self-contained files (no overlay), so the prod run can never accidentally pick up
dev settings.

**Check it's up:** open http://localhost:5173 (dev) or http://localhost (prod).
API health: `curl http://localhost:8000/api/health` (dev).

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

`backend/eval/run_eval.py` runs the real extractor over hand-written fixtures and
reports two things:

- **Grounding (model-free):** every finding's `evidence` must appear verbatim in a
  user message — the hard guard against hallucinated quotes.
- **Label micro & macro F1** (after the confidence floor) vs. expected labels.
- **Abstention rate:** how many empty-expected fixtures correctly yield no findings.

```bash
cd backend && python -m eval.run_eval     # only the extractor calls the API
```

The 16 fixtures are deliberately CheckList-style: clear single-emotion cases, a
neutral control, **adversarial empty-expected probes** for over-attribution
(third-person emotion, past-and-resolved, negation, media subject, physical
fatigue, hypotheticals), **confusion pairs** (anxiety/fear, guilt/shame,
anger/frustration, sadness/disappointment), and a multi-label case.

Current run: **micro F1 0.95, macro F1 0.95, abstention 6/7, grounding 11/11.**
The one miss is honest signal — a resolved past annoyance was scored as
frustration — which is exactly what the hard fixtures are there to surface. This
is a small hand-written suite (validation, not a general-accuracy claim); a larger
human-labeled set is a "with another week" item.

## Deployment

**Live demo:** **https://16-171-160-96.sslip.io** · sign up with any email + password
(it's open), then start a conversation.

Deployed on a cloud VM (AWS EC2 free tier) with Docker Compose: Caddy serves the
built SPA and reverse-proxies `/api`, with automatic HTTPS via Let's Encrypt using
an `sslip.io` hostname (no domain to buy). Reproducible on any fresh VM:

```bash
git clone <repo> && cd emotion-extraction-chat
cp backend/.env.example backend/.env
#   set OPENAI_API_KEY, a strong SESSION_SECRET, and COOKIE_SECURE=true
cd deploy
SITE_ADDRESS=<server-ip-with-dashes>.sslip.io \
  docker compose -f docker-compose.prod.yml up -d --build
```

Migrations run on container start; the app is then live at
`https://<server-ip-with-dashes>.sslip.io`.

## Assumptions (decisions under ambiguity)

The brief is deliberately underspecified; full rationale is in `ASSUMPTIONS.md`.
The decisions that shaped this build:

- **Who it serves.** Two interests pull apart — the person wants to be heard, the
  business wants structured negative emotions. Resolved by treating extraction as a
  *silent byproduct* of a conversation worth having on its own.
- **"Negative emotion" = a fixed 10-label taxonomy** — closed and *evaluable*,
  rather than guessing the "right" open-ended definition.
- **Analysis runs once at end of session** over the raw transcript, grounded in a
  verbatim quote, conservative, with a confidence floor.
- **Minimal auth** (email + password, signed httpOnly cookie) — no recovery / JWT;
  out of scope for a 2-day build where auth isn't scored.
- **Hosted on a cloud VM via Compose** (AWS EC2 free tier), HTTPS through Caddy +
  `sslip.io` (no domain).

## With another week

- A live / in-session emotion read-out — done in a way that doesn't make the user
  feel observed (deliberately cut for that reason).
- A cross-session trends dashboard — the real product value of keeping history.
- A larger, human-labeled eval set with borderline cases and richer metrics.
- A prose "mirror of your day" summary alongside the structured findings.
- Production hardening: real auth (JWT + refresh, password recovery), and moving
  infra to a major cloud (GCP/AWS).
