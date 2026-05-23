"""Pydantic request/response models for the auth API.

Kept separate from the ORM models: these define the HTTP contract (and input
validation) the frontend mirrors, while ``db/models.py`` defines persistence.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings
from app.db.enums import ConversationStatus, MessageRole


def _normalize_email(value: str) -> str:
    """Trim and lowercase an email so lookups and the unique constraint are stable.

    Lowercasing the whole address (not just the domain) is a pragmatic choice: it
    prevents duplicate accounts that differ only by case, which matters more here
    than honouring case-sensitive local parts.
    """
    return value.strip().lower()


NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalize_email)]


class SignupRequest(BaseModel):
    """Payload to create a new account."""

    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Payload to authenticate an existing account."""

    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """Public view of a user; never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class MessageOut(BaseModel):
    """A single conversation turn."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    """Summary of a conversation, without its messages (for lists)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ConversationStatus
    started_at: datetime
    ended_at: datetime | None


class ConversationDetail(ConversationOut):
    """A conversation together with its full message history."""

    messages: list[MessageOut]


class MessageCreate(BaseModel):
    """Payload to post a user message into a conversation."""

    content: str = Field(min_length=1, max_length=settings.max_message_chars)
