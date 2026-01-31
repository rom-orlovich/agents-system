from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base

if TYPE_CHECKING:
    from .task import Task


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Conversation(Base):
    __tablename__ = "conversations"

    source: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[str] = mapped_column(String(255))
    repository: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ConversationStatus.ACTIVE.value
    )
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="conversation")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation"
    )


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
