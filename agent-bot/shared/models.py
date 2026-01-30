import base64
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"


class WebhookProvider(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"


class Installation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None
    scopes: list[str]
    webhook_secret: str
    installed_by: str
    created_at: datetime
    updated_at: datetime


class InstallationCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None
    scopes: list[str]
    webhook_secret: str
    installed_by: str


class InstallationUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str | None = None
    refresh_token: str | None = None
    scopes: list[str] | None = None
    webhook_secret: str | None = None


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


class Message(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, str]
    created_at: datetime


class Conversation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    installation_id: str
    provider: Literal["github", "jira", "slack", "sentry"]
    external_id: str
    context: dict[str, str]
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = []


class ConversationContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    conversation_id: str
    messages: list[dict[str, str]]
    total_messages: int
    first_message_at: datetime
    last_message_at: datetime


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


class OAuthState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Literal["github", "slack", "jira"]
    redirect_uri: str
    nonce: str
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_encoded(self) -> str:
        json_str = self.model_dump_json()
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @classmethod
    def from_encoded(cls, encoded: str) -> "OAuthState":
        json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
        return cls.model_validate_json(json_str)


class OAuthCallbackParams(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    code: str
    state: str
    error: str | None = None
    error_description: str | None = None


class OAuthError(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    error: str
    error_description: str


class GitHubTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    token_type: str
    scope: str
    refresh_token: str | None = None
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None

    @computed_field
    @property
    def scopes(self) -> list[str]:
        return [s.strip() for s in self.scope.split(",") if s.strip()]


class GitHubInstallationInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    installation_id: int
    account_id: int
    account_login: str
    account_type: Literal["User", "Organization"]
    permissions: dict[str, str] = Field(default_factory=dict)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
