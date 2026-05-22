"""Database-lifecycle enums and the helper that maps them to Postgres ENUMs.

These describe the state machine of rows (status, role) and are distinct from the
negative-emotion *taxonomy* in ``app.llm.taxonomy``, which is the domain vocabulary
shared with the LLM layer and the frontend.
"""

from enum import Enum

from sqlalchemy import Enum as SAEnum


class ConversationStatus(str, Enum):
    """Lifecycle of a conversation."""

    ACTIVE = "active"
    ANALYZED = "analyzed"


class MessageRole(str, Enum):
    """Author of a message."""

    USER = "user"
    ASSISTANT = "assistant"


def pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Build a Postgres ENUM that stores the member *value*, not its name.

    SQLAlchemy defaults to persisting ``Enum.name`` (e.g. ``STRESS``); we want the
    value (``stress/overwhelm``) so the DB matches what the model returns and what
    the API/eval see. ``inherit_schema`` keeps the ENUM type in the same schema as
    its table rather than leaking into ``public``.
    """
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        inherit_schema=True,
    )
