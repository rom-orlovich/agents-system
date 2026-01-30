from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class AgentTask(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str
    provider: Literal["github", "jira", "slack", "sentry"]
    event_type: str
    installation_id: str
    organization_id: str
    input_message: str
    source_metadata: dict[str, str]
    priority: int
    created_at: datetime


class AgentContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task: AgentTask
    conversation_history: list[dict[str, str]] = []
    repository_path: str | None = None
    additional_context: dict[str, str] = {}


class AgentResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    output: str
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    error: str | None = None
    metadata: dict[str, str] = {}


class PlanStep(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    step_id: str
    action: Literal["analyze", "implement", "verify", "post"]
    description: str
    agent_type: str
    dependencies: list[str] = []


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    plan_id: str
    task_id: str
    steps: list[PlanStep]
    estimated_duration_seconds: float
