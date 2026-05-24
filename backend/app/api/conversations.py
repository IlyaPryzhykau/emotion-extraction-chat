"""Conversations API: create, list, and fetch a conversation with its messages.

The streaming message endpoint lives separately (added next); this router covers
the CRUD-ish lifecycle. Every route is scoped to the authenticated user.
"""

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import OpenAIError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import (
    ConversationDetail,
    ConversationListItem,
    ConversationOut,
    EmotionOut,
    MessageCreate,
)
from app.core.config import settings
from app.db.base import get_db
from app.db.enums import ConversationStatus, MessageRole
from app.db.models import User
from app.llm.client import stream_chat
from app.services import conversation_service, emotion_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationListItem, status_code=status.HTTP_201_CREATED)
def create_conversation(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ConversationListItem:
    """Start a new conversation (no findings yet, so labels are empty)."""
    conversation = conversation_service.create_conversation(db, user)
    return ConversationListItem(
        id=conversation.id,
        status=conversation.status,
        started_at=conversation.started_at,
        ended_at=conversation.ended_at,
        labels=[],
    )


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConversationListItem]:
    """List the current user's conversations (most recent first) with their labels."""
    return [
        ConversationListItem(
            id=conversation.id,
            status=conversation.status,
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            labels=labels,
        )
        for conversation, labels in conversation_service.list_conversations_with_labels(db, user)
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Fetch one conversation with its full message history."""
    conversation = conversation_service.get_conversation(db, user, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conversation


def _sse(payload: dict[str, object]) -> str:
    """Format one Server-Sent Event line (JSON-encoded so newlines are safe).

    ``ensure_ascii=False`` keeps non-ASCII (emoji, accents) readable UTF-8 in the
    stream rather than ``\\uXXXX`` escapes; the response is served as utf-8.
    """
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/{conversation_id}/messages")
def post_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Post a user message and stream the assistant's reply as Server-Sent Events.

    Emits ``{"delta": "..."}`` events as tokens arrive, then a final
    ``{"done": true, "message_id": "..."}``. The assistant turn is persisted once
    streaming completes.
    """
    conversation = conversation_service.get_conversation(db, user, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    if conversation.status is not ConversationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This conversation has been analyzed and is closed.",
        )

    turns = conversation_service.count_user_turns(db, conversation)
    if turns >= settings.hard_cap_turns:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This conversation has reached its length limit; end & analyze it.",
        )

    conversation_service.add_message(db, conversation, MessageRole.USER, payload.content)
    # Wind down once this turn pushes us past the soft threshold.
    wind_down = (turns + 1) >= settings.soft_wind_down_turns
    chat_messages = conversation_service.build_chat_messages(db, conversation, wind_down)

    def event_stream() -> Iterator[str]:
        # The SSE response is already 200 with headers flushed by the time tokens
        # stream, so failures are reported as an {"error": ...} event, not a status
        # code — the client must inspect events. We catch only OpenAI errors so a
        # genuine bug still surfaces loudly rather than masquerading as "unavailable".
        parts: list[str] = []
        try:
            for delta in stream_chat(chat_messages):
                parts.append(delta)
                yield _sse({"delta": delta})
        except OpenAIError:
            # The user's message is already saved, so they can retry.
            yield _sse({"error": "The assistant is unavailable right now."})
            return
        assistant = conversation_service.add_message(
            db, conversation, MessageRole.ASSISTANT, "".join(parts)
        )
        yield _sse({"done": True, "message_id": str(assistant.id)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{conversation_id}/analyze", response_model=list[EmotionOut])
def analyze_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmotionOut]:
    """End the conversation and run the one-shot emotion analysis over it."""
    conversation = conversation_service.get_conversation(db, user, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    if conversation.status is not ConversationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This conversation has already been analyzed.",
        )
    if conversation_service.count_user_turns(db, conversation) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There's nothing to analyze yet — say something first.",
        )
    try:
        return emotion_service.analyze_conversation(db, conversation)
    except (OpenAIError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis is unavailable right now; please try again.",
        )


@router.get("/{conversation_id}/report", response_model=list[EmotionOut])
def get_report(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmotionOut]:
    """Return the stored emotion findings for a conversation (empty if none)."""
    conversation = conversation_service.get_conversation(db, user, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return emotion_service.list_emotions(db, conversation)
