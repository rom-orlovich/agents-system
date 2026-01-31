from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class TaskEventType(StrEnum):
    WEBHOOK_RECEIVED = "webhook:received"
    WEBHOOK_VALIDATED = "webhook:validated"
    WEBHOOK_MATCHED = "webhook:matched"
    WEBHOOK_TASK_CREATED = "webhook:task_created"
    TASK_CREATED = "task:created"
    TASK_STARTED = "task:started"
    TASK_OUTPUT = "task:output"
    TASK_USER_INPUT = "task:user_input"
    TASK_METRICS = "task:metrics"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"


class TaskEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    type: TaskEventType
    task_id: Optional[str] = None
    webhook_event_id: Optional[str] = None
    timestamp: datetime
    data: dict


class TaskMetadata(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str
    source: Literal["dashboard", "webhook", "api"]
    provider: Optional[str] = None
    created_at: datetime
    assigned_agent: str
    model: str


class WebhookEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    timestamp: str
    stage: str
    data: dict


class AgentOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    timestamp: str
    type: str
    content: str
    tool: Optional[str] = None
    params: Optional[dict] = None


class UserInput(BaseModel):
    model_config = ConfigDict(strict=True)

    timestamp: str
    type: Literal["user_response"]
    question_type: str
    content: str


class FinalResult(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    metrics: Optional[dict] = None
    completed_at: str
