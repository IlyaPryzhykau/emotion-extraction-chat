"""Thin OpenAI client wrapper.

All OpenAI specifics live here so the rest of the app depends on small, typed
functions rather than the SDK. The conversation uses the cheap model and streams
tokens; the one-shot analysis (added later) will use the strong model.
"""

from collections.abc import Iterator

from openai import OpenAI

from app.core.config import settings

ChatMessage = dict[str, str]  # {"role": ..., "content": ...}

_client = OpenAI(api_key=settings.openai_api_key)


def stream_chat(messages: list[ChatMessage], model: str | None = None) -> Iterator[str]:
    """Stream assistant text deltas for a chat conversation.

    Args:
        messages: Full message list (system + prior turns), OpenAI format.
        model: Override the model; defaults to the cheap chat model.

    Yields:
        Content fragments as they arrive, in order. Empty deltas are skipped.
    """
    stream = _client.chat.completions.create(
        model=model or settings.chat_model,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        # Some chunks (e.g. a trailing usage-only chunk) carry no choices.
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
