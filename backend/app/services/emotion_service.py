"""Emotion analysis: run the extractor over a conversation and persist findings.

This is the authoritative end-of-session pass. It reads the full raw transcript,
asks the analyst model for structured findings, drops anything below the
confidence floor, stores the findings, and marks the conversation analyzed.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.enums import ConversationStatus
from app.db.models import Conversation, Emotion, Message
from app.llm.extractor import extract_emotions


def analyze_conversation(db: Session, conversation: Conversation) -> list[Emotion]:
    """Extract emotions from the transcript, persist them, and close the session.

    Returns the stored findings (possibly empty — a calm day is a valid result).
    """
    transcript = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
    )
    extraction = extract_emotions(transcript)

    emotions = [
        Emotion(
            conversation_id=conversation.id,
            label=finding.label,
            intensity=finding.intensity,
            trigger=finding.trigger,
            evidence=finding.evidence,
            confidence=finding.confidence,
        )
        for finding in extraction.findings
        if finding.confidence >= settings.extraction_min_confidence
    ]
    db.add_all(emotions)

    conversation.status = ConversationStatus.ANALYZED
    conversation.ended_at = datetime.now(timezone.utc)
    db.commit()
    return emotions


def list_emotions(db: Session, conversation: Conversation) -> list[Emotion]:
    """Return the stored findings for a conversation (empty if not analyzed)."""
    stmt = (
        select(Emotion)
        .where(Emotion.conversation_id == conversation.id)
        .order_by(Emotion.created_at)
    )
    return list(db.scalars(stmt))
