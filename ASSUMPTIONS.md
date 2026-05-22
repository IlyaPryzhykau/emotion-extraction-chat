# Assumptions

The brief is deliberately underspecified. Rather than asking the client to fill the
gaps, we made these decisions and defend them here (and on the call). This file is
the living record; its content is mirrored into the README on submission.

## Product framing

- **Who the app serves.** The app serves *two* parties whose interests pull apart:
  the human (wants to be heard) and the business (wants structured negative
  emotions). We resolved this by treating extraction as a **silent byproduct of a
  conversation worth having on its own**. The end report is framed first as an
  honest mirror for the user, second as a business artifact.
  *Why:* an interrogation-style app produces guarded users and junk data; a warm
  listener produces real signal. This is the central judgment call.

- **"Negative emotion" = a fixed taxonomy of 10 labels:** sadness, anxiety, anger,
  frustration, fear, guilt, shame, loneliness, disappointment, stress/overwhelm.
  *Why:* a closed set is defensible and *evaluable* (precision/recall) where
  open-ended labels are not. The brief explicitly says there is no "right"
  definition, so we picked a clear, defensible one.

## Extraction

- **Authoritative extraction happens once, at end of session**, over the full raw
  transcript — not per message.
  *Why:* bounded cost, full context, simplest correct thing. Per-message is a
  "with another week" item.

- **No summarization before extraction.** The extractor reads raw messages.
  *Why:* summarization discards the exact wording and tone that carry the emotional
  signal we are trying to extract.

- **No live / mid-conversation emotion read-out, and no `source` column.** Emotions
  are produced once, in the end-of-session report; there is no provisional read-out
  while the user talks, so every stored finding is authoritative by construction.
  *Why:* a running read-out makes the user feel scored as they speak (contradicts the
  framing), has worse quality on partial context, and costs extra per-turn calls.
  Since only end-of-session findings exist, a `source` discriminator column would have
  a single value — so we don't add one (YAGNI/KISS). A future read-out is a "with
  another week" item and would introduce the column then, when it earns its place.

- **Every extracted finding must be grounded** in a verbatim quote + message id, and
  the eval harness rejects evidence that does not appear in the transcript.
  *Why:* "approximate correctness is not acceptable" → no ungrounded/hallucinated
  emotions.

## Conversation flow & cost

- **The user ends the session** ("End & analyze") whenever they want.
- **Soft wind-down ~25–30 user turns**, **hard cap ~60 user turns**, **~2000 char
  per-message limit**.
  *Why:* let people actually vent without an abrupt cut, while capping runaway cost
  and abuse. Running on personal API credits is itself a constraint to respect.

- **Cheap model for the conversation, strong model once for analysis.** Model IDs
  are env vars (`CHAT_MODEL`, `EXTRACTION_MODEL`); `scripts/list_models.py` confirms
  what is actually available so we never ship a stale model string.

## Auth & scope

- **Minimal auth:** signup/login/logout, bcrypt hash, one signed httpOnly session
  cookie with an absolute 14-day expiry. **No refresh/rotation, no password
  recovery, no email verification, no OAuth/2FA.**
  *Why:* none of this earns its place in a 2-day build where auth is explicitly not
  scored — a single signed session is enough to scope data per user and demo the
  product. All of it (refresh tokens / sliding sessions, recovery, verification,
  OAuth) is straightforward to add and is a "with another week" item; we left it out
  rather than half-build it.

- **Multi-user** with per-user session history.
  *Why:* shows schema/scoping thinking and makes the trends story (the real product
  value) possible.

## Infrastructure

- **Hosted on an existing Hetzner VPS**, Docker Compose (caddy + app + db), HTTPS via
  Caddy + `sslip.io` (no domain purchase).
  *Why:* zero hosting cost on hardware we already have, full end-to-end ownership of
  the deploy. For production we would use a major cloud (GCP/AWS) — a "with another
  week" item.

- **Postgres**, not SQLite. App tables/enums live in a dedicated `app` schema, not
  `public`.
  *Why:* matches a realistic production stack and the trends/history use case; a
  dedicated schema keeps ownership explicit.

- **UUIDv4 primary keys, generated app-side** (native Postgres `UUID` type), not
  auto-increment integers.
  *Why:* IDs appear in URLs, so non-enumerable keys are a sound production default;
  per-user authorization already blocks cross-user access, so this is
  defense-in-depth, not the only guard. Chose v4 for zero dependencies (stdlib
  `uuid.uuid4`); UUIDv7 (time-ordered, better B-tree index locality) is the
  refinement once write volume matters — a "with another week" item.

- **Schema is managed by Alembic migrations**, not by the app at startup. Migrations
  run as an explicit step (`alembic upgrade head`) before the app serves traffic; the
  app process itself performs no DDL.
  *Why:* versioned, reviewable schema changes and a clean upgrade/downgrade path —
  the production-correct approach, and it sidesteps any startup race if the backend
  is ever scaled to multiple replicas. (The downgrade also drops the ENUM types,
  which Postgres otherwise leaves behind after a table drop.)
