from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class UsageMetric(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    task_id: str
    installation_id: str
    provider: Literal["github", "jira", "slack", "sentry"]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    created_at: datetime


class TokenUsageSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    period: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    task_count: int


class CostSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    organization_id: str
    period: str
    total_cost_usd: float
    task_count: int
    average_cost_per_task: float


class ModelUsageSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    model: str
    period: str
    total_tokens: int
    total_cost_usd: float
    task_count: int


class OAuthTokenStatus(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    installation_id: str
    platform: str
    organization_id: str
    is_expired: bool
    expires_at: datetime | None
    last_used_at: datetime | None
