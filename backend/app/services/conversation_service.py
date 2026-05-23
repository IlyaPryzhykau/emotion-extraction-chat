"""Conversation lifecycle and ownership-scoped lookups.

Routers stay thin and call into here. Everything is scoped to the owning user;
lookups for a conversation the user doesn't own return None (the router turns
that into a 404, so we never reveal that someone else's conversation exists).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, User


def create_conversation(db: Session, user: User) -> Conversation:
    """Start a new active conversation for ``user``."""
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.commit()
    return conversation


def list_conversations(db: Session, user: User) -> list[Conversation]:
    """Return the user's conversations, most recent first."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.started_at.desc())
    )
    return list(db.scalars(stmt))


def get_conversation(
    db: Session, user: User, conversation_id: uuid.UUID
) -> Conversation | None:
    """Return the user's conversation by id, or None if missing or not theirs."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user.id
    )
    return db.scalar(stmt)
