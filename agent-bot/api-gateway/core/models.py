from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WebhookProvider(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    input_message: str = Field(..., min_length=1)
    assigned_agent: str | None = Field(None)
    agent_type: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_metadata: dict[str, str | int | bool] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    task_id: str | None = Field(None)
    message: str
    error: str | None = Field(None)


class GitHubWebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    action: str = Field(..., min_length=1)
    repository: dict[str, str | int | bool] = Field(...)
    issue: dict[str, str | int | bool] | None = Field(None)
    pull_request: dict[str, str | int | bool] | None = Field(None)
    comment: dict[str, str | int] | None = Field(None)
    sender: dict[str, str | int | bool] = Field(...)


class JiraWebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    webhookEvent: str = Field(..., min_length=1)
    issue: dict[str, str | int | bool | dict] = Field(...)
    user: dict[str, str] | None = Field(None)
    comment: dict[str, str | dict] | None = Field(None)


class SlackWebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str = Field(..., min_length=1)
    event: dict[str, str | int | bool | list] | None = Field(None)
    challenge: str | None = Field(None)


class SentryWebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    action: str = Field(..., min_length=1)
    data: dict[str, str | int | bool | dict | list] = Field(...)
    actor: dict[str, str | int] | None = Field(None)
