"""Print the OpenAI models available to the configured API key.

We do not hard-code model IDs anywhere meaningful (they live in env). Run this
before deploy to confirm the exact strings to put in CHAT_MODEL / EXTRACTION_MODEL,
so we never ship a stale name that 404s.

Usage:
    python scripts/list_models.py
"""

from openai import OpenAI

from app.core.config import settings


def main() -> None:
    """List model IDs the current API key can access, sorted alphabetically."""
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set; populate backend/.env first.")

    client = OpenAI(api_key=settings.openai_api_key)
    model_ids = sorted(model.id for model in client.models.list())

    print(f"{len(model_ids)} models available to this key:\n")
    for model_id in model_ids:
        print(f"  {model_id}")

    print(
        "\nCurrent config:\n"
        f"  CHAT_MODEL       = {settings.chat_model}\n"
        f"  EXTRACTION_MODEL = {settings.extraction_model}"
    )


if __name__ == "__main__":
    main()
