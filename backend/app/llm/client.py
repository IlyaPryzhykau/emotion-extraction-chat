"""Thin OpenAI client wrapper.

All OpenAI specifics live here so the rest of the app depends on small, typed
functions rather than the SDK. The conversation uses the cheap model and streams
tokens; the one-shot analysis (added later) will use the strong model.
"""

from collections.abc import Iterator
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings

ChatMessage = dict[str, str]  # {"role": ..., "content": ...}

T = TypeVar("T", bound=BaseModel)

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


def parse_structured(
    messages: list[ChatMessage], response_format: type[T], model: str | None = None
) -> T:
    """Call the model in structured-output mode and return the parsed object.

    Used for the one-shot analysis (the strong model). Raises if the model fails
    to return a parseable result so the caller can surface a clean error.
    """
    completion = _client.beta.chat.completions.parse(
        model=model or settings.extraction_model,
        messages=messages,
        response_format=response_format,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Model returned no structured output")
    return parsed
