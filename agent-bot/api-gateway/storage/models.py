from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Float,
    Text,
    Boolean,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime, timezone
from storage.database import Base
from core.models import TaskStatus, WebhookProvider
import uuid


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    input_message = Column(Text, nullable=False)
    assigned_agent = Column(String(64), nullable=True)
    agent_type = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    status = Column(
        SQLEnum(TaskStatus), default=TaskStatus.QUEUED, nullable=False, index=True
    )
    source_metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
        Index("idx_user_created", "user_id", "created_at"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    provider = Column(SQLEnum(WebhookProvider), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB, nullable=False)
    signature_valid = Column(Boolean, default=False, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("idx_provider_created", "provider", "created_at"),
        Index("idx_processed_created", "processed", "created_at"),
    )


class TaskResult(Base):
    __tablename__ = "task_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    cost_usd = Column(Float, default=0.0, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (Index("idx_task_result", "task_id", "created_at"),)


class APICall(Base):
    __tablename__ = "api_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(64), nullable=False, index=True)
    service = Column(String(64), nullable=False, index=True)
    endpoint = Column(String(256), nullable=False)
    method = Column(String(16), nullable=False)
    request_payload = Column(JSONB, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_payload = Column(JSONB, nullable=True)
    duration_ms = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("idx_task_service", "task_id", "service"),
        Index("idx_service_created", "service", "created_at"),
    )
