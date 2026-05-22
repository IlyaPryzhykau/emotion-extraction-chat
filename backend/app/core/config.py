"""Application configuration.

All runtime configuration is read from the environment so nothing secret or
deploy-specific is baked into the code (see CLAUDE.md "Cost discipline" and
"No secrets in code"). A single ``settings`` instance is imported wherever
configuration is needed.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from environment variables.

    Model IDs are intentionally configurable rather than hard-coded: the exact
    available model names change over time, so we resolve them at deploy time
    (see ``scripts/list_models.py``) instead of risking a stale string that 404s.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/emotions"
    # All app tables/enums live in this Postgres schema, not public.
    db_schema: str = "app"

    openai_api_key: str = ""
    # Cheap/fast model: drives the conversation and the lightweight live classifier.
    chat_model: str = "gpt-5.4-mini"
    # Strong model: used once per session for the authoritative extraction.
    extraction_model: str = "gpt-5.5"

    # MUST be overridden in production; used to sign the session cookie.
    session_secret: str = "dev-only-insecure-secret-change-me"
    session_max_age: int = 60 * 60 * 24 * 14  # seconds (14 days)

    # Conversation guardrails — cost & UX (PLAN §5).
    max_message_chars: int = 2000
    # Turn at which the assistant starts gently winding down (not a hard cut).
    soft_wind_down_turns: int = 28
    # Hard ceiling on user turns; runaway-cost guardrail, not a target.
    hard_cap_turns: int = 60


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so the environment is parsed once; tests can clear the cache to
    inject overrides.
    """
    return Settings()


settings = get_settings()
