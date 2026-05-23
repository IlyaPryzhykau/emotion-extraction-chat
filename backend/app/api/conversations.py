"""Conversations API: create, list, and fetch a conversation with its messages.

The streaming message endpoint lives separately (added next); this router covers
the CRUD-ish lifecycle. Every route is scoped to the authenticated user.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import ConversationDetail, ConversationOut
from app.db.base import get_db
from app.db.models import User
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ConversationOut:
    """Start a new conversation."""
    return conversation_service.create_conversation(db, user)


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConversationOut]:
    """List the current user's conversations, most recent first."""
    return conversation_service.list_conversations(db, user)


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
