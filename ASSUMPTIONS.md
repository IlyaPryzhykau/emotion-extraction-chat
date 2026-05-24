# Assumptions

The brief is deliberately underspecified, so these are the decisions I made and
why — the kind of thing I'd defend on the call rather than asking the client to
fill the gaps.

## Context (not given in the brief)

I treated the app as an **end-of-day journal**: you talk through your day and get a
wrap-up, while the product (or a third party) needs to know which **negative
emotions** you went through. So it serves two parties at once — the person wants to
be heard, the business wants structured emotions. I resolved that by making
extraction a **silent byproduct of a conversation worth having on its own**: the
companion just listens, and the analysis happens separately afterward.

The conversation is **English-only** (per the brief): even if the user writes in
another language, the companion gently keeps replying in English.

## Stack, and why

- **Backend:** Python + FastAPI + Postgres — my main stack.
- **Frontend:** React + TypeScript — not my home turf, but I got there with Claude.
- **LLM:** OpenAI `gpt-5.4-mini` for the conversation (cheap/fast), `gpt-5.5` once at
  the end for the analysis.

## What I built in 2 days

A simple app that holds a conversation and, once you end it, analyzes the whole
transcript and extracts the negative emotions you expressed during the day.

## Data model (4 entities)

- **User** — identity / account.
- **Conversation** — one session, owned by a user.
- **Message** — a turn, belongs to a conversation.
- **Emotion** — a finding, belongs to an analyzed conversation.

## The conversation

- A plain **listener** prompt: it doesn't fish for emotions or hint at them — it
  just listens, so the data isn't biased by leading questions.
- Up to ~60 user turns; after ~28 a nudge is mixed into the prompt to gently steer
  toward wrapping up. Feels like enough room to vent, but this deserves real research.
- **Safety:** if someone signals crisis / self-harm, the companion gently points
  them to someone they trust or a professional (no hardcoded numbers — geo-agnostic).
- **Cost:** the cheap model drives the chat, the strong model runs only once for the
  analysis (this is on personal API credits).

## The analysis

- A **composite prompt**: (1) analysis instructions, (2) the emotion list with
  descriptions for the model. The request also carries a **response schema**
  (structured output) so I can parse it straight into the DB.
- Each finding is **grounded in a verbatim quote** from the user, which guards
  against hallucinated emotions; the eval harness rejects any evidence that isn't in
  the transcript.
- **Conservative:** an empty result is valid (an okay day), and a confidence floor
  drops weak guesses — over-attribution is the main failure mode for this kind of
  extraction.
- I didn't deep-research the psychology / interviewing side here — that needs more
  time.

## Emotion taxonomy

A fixed **enum of 10 negative emotions** with short descriptions for the model, so
there's no drift in how it labels. A closed set is also *evaluable* (precision /
recall) where open-ended labels aren't. Model IDs live in env, and
`scripts/list_models.py` confirms what the key can actually use.

## Auth

Simple: a **signed session cookie kept ~14 days** in the browser. I didn't build
JWT / OAuth — auth isn't the focus of this task. The cookie is httpOnly (JS can't
read it), every query is scoped per user (someone else's conversation returns 404),
and the login check is constant-time so you can't probe which emails are registered.

## Why SSE for the chat

The reply streams over **Server-Sent Events** — the server pushes tokens over one
long-lived HTTP response, so the text appears as it's generated. I picked SSE over
WebSocket because the flow is one-directional (server → client), it's plain HTTP
(passes cleanly through Caddy, has built-in reconnect), and it's simpler than a
bidirectional socket we don't need. On short chats the latency win is small — it's
mostly UX polish — but it's the right primitive and cheap. (The frontend reads it
via `fetch` + `ReadableStream`, since native `EventSource` can't POST a body.)

## Tests / eval

There are eval fixtures for the analysis prompt and the model's output — currently
**F1 ≈ 0.95**, but that's really just "it basically works." I'd want a psychologist
to write more interesting, borderline cases. Backend tests run against a real
Postgres with per-test transaction rollback; the LLM is mocked.

## Infrastructure

- **UUIDv4** primary keys, so IDs exposed in URLs aren't enumerable.
- A dedicated Postgres schema (`emotion_extraction_chat`), not `public`.
- Schema managed by **Alembic** migrations, not `create_all` at startup.
- Deployed on **AWS EC2 (free tier) with Docker Compose + Caddy**; HTTPS via
  `sslip.io`, so no domain to buy.

## With another week

- **Auth:** JWT or Google sign-in, proper logout, change password, and "kill tokens
  on all devices."
- **Companion:** research and test the prompt more; maybe several **personality
  types** — adapt or auto-pick from past conversations, or read the mood from the
  first messages and switch.
- **Analysis:** improve the prompt and the eval cases for a more honest read on the
  model.
- **UI:** polish.
- **Cross-session trends** — a "what's been weighing on you this week" dashboard,
  which is the real value of keeping history.
- A prose **"mirror of your day"** summary alongside the structured findings.
- A **psychologist-labeled eval set**, plus per-message extraction with an emotion
  timeline within a session.
