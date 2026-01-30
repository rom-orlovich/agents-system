"""Base models and shared types."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4


class BaseResponse(BaseModel):
    """Base response model."""

    model_config = ConfigDict(strict=True, frozen=True)

    success: bool
    message: str
    data: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(strict=True, frozen=True)

    status: Literal["healthy", "unhealthy"]
    service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] | None = None


class TaskStatus(BaseModel):
    """Task status information."""

    model_config = ConfigDict(strict=True)

    task_id: UUID = Field(default_factory=uuid4)
    status: Literal["pending", "in_progress", "completed", "failed"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None
    result: dict[str, Any] | None = None


class WebhookEvent(BaseModel):
    """Generic webhook event."""

    model_config = ConfigDict(strict=True)

    event_id: UUID = Field(default_factory=uuid4)
    source: Literal["github", "jira", "slack", "sentry"]
    event_type: str
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=datetime.utcnow)
    signature: str | None = None


class TaskRequest(BaseModel):
    """Task creation request."""

    model_config = ConfigDict(strict=True)

    task_type: Literal["planning", "execution", "verification"]
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    priority: Literal["low", "medium", "high"] = Field(default="medium")


class TaskResult(BaseModel):
    """Task execution result."""

    model_config = ConfigDict(strict=True, frozen=True)

    task_id: UUID
    status: Literal["completed", "failed"]
    duration_seconds: float
    output: dict[str, Any] | None = None
    error: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
