"""ORM models — the data model from PLAN §4.

Four tables: users, conversations, messages, emotions. Every emotion finding
carries a verbatim ``evidence`` quote as its grounding.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ConversationStatus, MessageRole, pg_enum
from app.llm.taxonomy import EmotionLabel, Intensity


class User(Base):
    """An authenticated user. Owns conversations.

    Attributes:
        id: Primary key — UUIDv4, generated app-side.
        email: Login identifier; unique, stored normalized (trimmed + lowercased).
        password_hash: bcrypt hash of the password; the plaintext is never stored.
        created_at: When the account was created.
        conversations: This user's conversations (deleted with the user).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """A single "talk about your day" session for one user.

    Attributes:
        id: Primary key — UUIDv4, generated app-side.
        user_id: Owning user; conversations are deleted with their user.
        status: ACTIVE while chatting; ANALYZED once the final report exists.
        started_at: When the session began.
        ended_at: When the user ended the session and analysis ran; NULL while active.
        user: The owning user.
        messages: Turns in this conversation, ordered by creation time.
        emotions: Findings extracted from this conversation.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True
    )
    status: Mapped[ConversationStatus] = mapped_column(
        pg_enum(ConversationStatus, "conversation_status"),
        default=ConversationStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        # UUID PKs aren't ordered; messages are sequenced by creation time (each is
        # committed in its own transaction, so timestamps are distinct).
        order_by="Message.created_at",
    )
    emotions: Mapped[list["Emotion"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """One turn in a conversation, from the user or the assistant.

    Attributes:
        id: Primary key — UUIDv4, generated app-side.
        conversation_id: Conversation this message belongs to.
        role: Who wrote it — USER or ASSISTANT.
        content: The message text.
        created_at: When the message was stored.
        conversation: The parent conversation.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Conversation.id, ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(pg_enum(MessageRole, "message_role"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Emotion(Base):
    """A single negative-emotion finding extracted from a conversation.

    Each finding is grounded in a verbatim ``evidence`` quote from the transcript
    (the eval harness separately verifies the quote actually appears there).

    Attributes:
        id: Primary key — UUIDv4, generated app-side.
        conversation_id: Conversation the finding came from.
        label: The negative emotion, from the fixed taxonomy.
        intensity: Coarse strength — low / medium / high.
        trigger: Short description of the cause, grounded in the conversation.
        evidence: Verbatim quote supporting the finding.
        confidence: Model's confidence in the finding, 0.0–1.0.
        created_at: When the finding was stored.
        conversation: The parent conversation.
    """

    __tablename__ = "emotions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Conversation.id, ondelete="CASCADE"), index=True
    )
    label: Mapped[EmotionLabel] = mapped_column(pg_enum(EmotionLabel, "emotion_label"))
    intensity: Mapped[Intensity] = mapped_column(pg_enum(Intensity, "emotion_intensity"))
    trigger: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="emotions")
