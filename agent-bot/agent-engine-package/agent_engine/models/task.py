from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskSource(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"
    INTERNAL = "internal"


class Task(Base):
    __tablename__ = "tasks"

    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value)
    source: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(100))
    repository: Mapped[str | None] = mapped_column(String(255), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=True,
    )

    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation", back_populates="tasks"
    )
    agent_executions: Mapped[list["AgentExecution"]] = relationship(
        "AgentExecution", back_populates="task"
    )


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
    )
    agent_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    input_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="agent_executions")


from .conversation import Conversation
