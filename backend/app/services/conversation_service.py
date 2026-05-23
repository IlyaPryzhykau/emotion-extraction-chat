"""Conversation lifecycle and ownership-scoped lookups.

Routers stay thin and call into here. Everything is scoped to the owning user;
lookups for a conversation the user doesn't own return None (the router turns
that into a 404, so we never reveal that someone else's conversation exists).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import MessageRole
from app.db.models import Conversation, Emotion, Message, User
from app.llm.client import ChatMessage
from app.llm.prompts import CONVERSATIONALIST_SYSTEM, WIND_DOWN_NUDGE
from app.llm.taxonomy import EmotionLabel


def create_conversation(db: Session, user: User) -> Conversation:
    """Start a new active conversation for ``user``."""
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.commit()
    return conversation


def list_conversations_with_labels(
    db: Session, user: User
) -> list[tuple[Conversation, list[EmotionLabel]]]:
    """Return the user's conversations (most recent first), each with its distinct
    extracted emotion labels.

    Two queries total regardless of count: one for the conversations, one for all
    their emotions — labels are then grouped in Python (avoids an N+1).
    """
    conversations = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.started_at.desc())
        )
    )
    if not conversations:
        return []

    rows = db.execute(
        select(Emotion.conversation_id, Emotion.label).where(
            Emotion.conversation_id.in_([c.id for c in conversations])
        )
    ).all()

    labels_by_conversation: dict[uuid.UUID, list[EmotionLabel]] = {}
    for conversation_id, label in rows:
        bucket = labels_by_conversation.setdefault(conversation_id, [])
        if label not in bucket:  # distinct, preserving first-seen order
            bucket.append(label)

    return [(c, labels_by_conversation.get(c.id, [])) for c in conversations]


def get_conversation(
    db: Session, user: User, conversation_id: uuid.UUID
) -> Conversation | None:
    """Return the user's conversation by id, or None if missing or not theirs."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user.id
    )
    return db.scalar(stmt)


def count_user_turns(db: Session, conversation: Conversation) -> int:
    """How many messages the user has sent in this conversation."""
    stmt = select(func.count()).where(
        Message.conversation_id == conversation.id, Message.role == MessageRole.USER
    )
    return db.scalar(stmt) or 0


def add_message(
    db: Session, conversation: Conversation, role: MessageRole, content: str
) -> Message:
    """Persist one message in a conversation."""
    message = Message(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    db.commit()
    return message


def build_chat_messages(
    db: Session, conversation: Conversation, wind_down: bool
) -> list[ChatMessage]:
    """Assemble the OpenAI message list: system prompt + full history.

    Reads the transcript fresh (ordered by creation time) so the just-saved user
    turn is included. ``wind_down`` adds a nudge to guide a gentle close.
    """
    messages: list[ChatMessage] = [
        {"role": "system", "content": CONVERSATIONALIST_SYSTEM}
    ]
    if wind_down:
        messages.append({"role": "system", "content": WIND_DOWN_NUDGE})

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    for message in db.scalars(stmt):
        messages.append({"role": message.role.value, "content": message.content})
    return messages
