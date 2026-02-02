"""
ALL domain models with Pydantic validation.
Business rules are ENFORCED here, not in service layer.
"""

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# =============================================================================
# ENUMS (String-based for JSON serialization)
# =============================================================================


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(StrEnum):
    """Built-in agent types."""

    PLANNING = "planning"
    EXECUTOR = "executor"
    CODE_IMPLEMENTATION = "code_implementation"
    QUESTION_ASKING = "question_asking"
    CONSULTATION = "consultation"
    CUSTOM = "custom"


class EntityType(StrEnum):
    """Dynamic entity types."""

    WEBHOOK = "webhook"
    AGENT = "agent"
    SKILL = "skill"


class AuthStatus(StrEnum):
    """Authentication states."""

    VALID = "valid"
    EXPIRED = "expired"
    REFRESH_NEEDED = "refresh_needed"
    MISSING = "missing"
    RATE_LIMITED = "rate_limited"


# =============================================================================
# BASE CONFIGURATION
# =============================================================================


class MachineConfig(BaseModel):
    """Machine configuration with Pydantic Settings."""

    model_config = ConfigDict(frozen=True)

    machine_id: str = Field(..., min_length=1, max_length=64)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=20)
    task_timeout_seconds: int = Field(default=3600, ge=60, le=86400)
    data_dir: Path = Field(default=Path("/data"))

    @field_validator("machine_id")
    @classmethod
    def validate_machine_id(cls, v: str) -> str:
        """Machine ID must be alphanumeric with hyphens."""
        import re

        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("machine_id must be alphanumeric with hyphens only")
        return v


# =============================================================================
# SESSION MODEL (Per-User Tracking)
# =============================================================================


class Session(BaseModel):
    """Dashboard session with per-user tracking."""

    model_config = ConfigDict(validate_assignment=True)

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User account ID from Claude auth")
    machine_id: str = Field(..., description="Machine this session connects to")
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disconnected_at: Optional[datetime] = None

    # Metrics (auto-updated)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_tasks: int = Field(default=0, ge=0)
    active_task_ids: List[str] = Field(default_factory=list)

    @field_validator("session_id", "user_id", "machine_id")
    @classmethod
    def validate_required_id(cls, v: str) -> str:
        """IDs cannot be empty."""
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()

    def add_task(self, task_id: str) -> None:
        """Add task to this session."""
        if task_id not in self.active_task_ids:
            self.active_task_ids.append(task_id)
            self.total_tasks += 1

    def add_cost(self, cost: float) -> None:
        """Add cost to session total."""
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        self.total_cost_usd += cost


# =============================================================================
# TASK MODEL (With Streaming Support)
# =============================================================================


class Task(BaseModel):
    """Task with full lifecycle and streaming support."""

    model_config = ConfigDict(validate_assignment=True)

    task_id: str = Field(..., description="Unique task identifier")
    session_id: str = Field(..., description="Session that created this task")
    user_id: str = Field(..., description="User who owns this task")

    # Assignment
    assigned_agent: Optional[str] = Field(None, description="Sub-agent handling this")
    agent_type: AgentType = Field(default=AgentType.PLANNING)

    # Status
    status: TaskStatus = Field(default=TaskStatus.QUEUED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Input/Output
    input_message: str = Field(..., min_length=1)
    output_stream: str = Field(default="", description="Accumulated output")
    result: Optional[str] = None
    error: Optional[str] = None

    # Metrics
    cost_usd: float = Field(default=0.0, ge=0.0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)

    # Relationships
    parent_task_id: Optional[str] = None
    source: Literal["dashboard", "webhook", "api"] = "dashboard"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_transitions(self) -> "Task":
        """Ensure valid status transitions."""
        if self.status == TaskStatus.RUNNING and self.started_at is None:
            object.__setattr__(self, "started_at", datetime.now(timezone.utc))
        if self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            if self.completed_at is None:
                object.__setattr__(self, "completed_at", datetime.now(timezone.utc))
            if self.started_at and self.completed_at:
                object.__setattr__(
                    self,
                    "duration_seconds",
                    (self.completed_at - self.started_at).total_seconds(),
                )
        return self

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {
                TaskStatus.WAITING_INPUT,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.WAITING_INPUT: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.COMPLETED: set(),  # Terminal
            TaskStatus.FAILED: set(),  # Terminal
            TaskStatus.CANCELLED: set(),  # Terminal
        }
        return new_status in valid_transitions.get(self.status, set())

    def transition_to(self, new_status: TaskStatus) -> None:
        """Transition to new status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status


# =============================================================================
# SUB-AGENT MODEL
# =============================================================================


class SubAgentConfig(BaseModel):
    """Sub-agent configuration."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    agent_type: AgentType = Field(default=AgentType.CUSTOM)
    description: str = Field(default="")
    skill_path: Path = Field(...)

    # Execution config
    max_concurrent: int = Field(default=1, ge=1, le=10)
    timeout_seconds: int = Field(default=3600, ge=60)
    priority: int = Field(default=0, ge=0, le=100)

    # Built-in vs dynamic
    is_builtin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must be lowercase alphanumeric with hyphens/underscores."""
        import re

        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "name must be lowercase alphanumeric with hyphens/underscores"
            )
        return v


# =============================================================================
# WEBHOOK MODEL
# =============================================================================


class WebhookCommand(BaseModel):
    """A command that can be triggered via webhook."""

    name: str = Field(..., description="Command name, e.g. 'approve', 'improve'")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    description: str = Field(default="")
    target_agent: str = Field(..., description="Which agent handles this command")
    prompt_template: Optional[str] = Field(
        None, description="Inline prompt template with {placeholders}"
    )
    template_file: Optional[str] = Field(
        None, description="Template file name (without .md extension)"
    )
    requires_approval: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "name must be lowercase alphanumeric with hyphens/underscores"
            )
        return v

    @model_validator(mode="after")
    def validate_template_source(self) -> "WebhookCommand":
        """Ensure either prompt_template or template_file is provided."""
        if not self.prompt_template and not self.template_file:
            raise ValueError("Either prompt_template or template_file must be provided")
        return self


class WebhookConfig(BaseModel):
    """Complete webhook configuration with commands."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    endpoint: str = Field(..., pattern=r"^/webhooks/[a-z0-9-]+$")
    source: Literal["github", "jira", "sentry", "slack", "gitlab", "custom"] = "custom"
    description: str = Field(default="")

    # Commands this webhook supports
    commands: List[WebhookCommand] = Field(default_factory=list)

    # Default command when no specific command is detected
    default_command: Optional[str] = None

    # Command prefix for detection (e.g., "@agent" or "/claude")
    command_prefix: str = Field(default="@agent")

    # Handler
    handler_path: Optional[Path] = None
    target_agent: str = Field(..., description="Agent to route tasks to")

    # Security
    requires_signature: bool = Field(default=True)
    signature_header: Optional[str] = Field(default=None)
    secret_env_var: Optional[str] = Field(default=None)

    # Metadata
    is_builtin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must be lowercase alphanumeric with hyphens."""
        import re

        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("name must be lowercase alphanumeric with hyphens")
        return v


# =============================================================================
# YAML WEBHOOK CONFIG MODELS (for easy config.yaml files)
# =============================================================================


class CommandYamlConfig(BaseModel):
    """YAML-friendly command configuration."""

    name: str = Field(..., description="Command name, e.g. 'approve', 'review'")
    aliases: List[str] = Field(
        default_factory=list, description="Alternative trigger names"
    )
    description: str = Field(default="", description="Human-readable description")
    target_agent: str = Field(
        default="planning", description="Which agent handles this command"
    )
    prompt_template: Optional[str] = Field(
        None, description="Inline prompt template with {{placeholders}}"
    )
    template_file: Optional[str] = Field(
        None, description="Template file name (without .md extension)"
    )
    requires_approval: bool = Field(
        default=False, description="Whether approval is needed"
    )

    @model_validator(mode="after")
    def validate_template_source(self) -> "CommandYamlConfig":
        """Ensure either prompt_template or template_file is provided."""
        if not self.prompt_template and not self.template_file:
            raise ValueError("Either prompt_template or template_file must be provided")
        return self

    def to_webhook_command(self) -> "WebhookCommand":
        """Convert to WebhookCommand model."""
        return WebhookCommand(
            name=self.name,
            aliases=self.aliases,
            description=self.description,
            target_agent=self.target_agent,
            prompt_template=self.prompt_template,
            template_file=self.template_file,
            requires_approval=self.requires_approval,
        )


class AgentTriggerConfig(BaseModel):
    """Configuration for how to trigger the agent."""

    prefix: str = Field(
        default="@agent", description="Command prefix (e.g. '@agent', '@claude')"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative prefixes/names (e.g. ['@claude', '@bot'])",
    )
    # For Jira: the assignee name that triggers the agent
    assignee_trigger: Optional[str] = Field(
        default=None, description="For Jira: assignee name that triggers the agent"
    )


class SecurityConfig(BaseModel):
    """Webhook security configuration."""

    requires_signature: bool = Field(
        default=True, description="Require signature verification"
    )
    signature_header: Optional[str] = Field(
        default=None,
        description="Header name for signature (e.g. 'X-Hub-Signature-256')",
    )
    secret_env_var: Optional[str] = Field(
        default=None, description="Environment variable name for webhook secret"
    )


class WebhookYamlConfig(BaseModel):
    """
    YAML-friendly webhook configuration.

    This model is designed for easy editing in config.yaml files.
    Each webhook folder has its own config.yaml with this structure.
    """

    # Basic info
    name: str = Field(..., description="Webhook name (e.g. 'github', 'jira')")
    description: str = Field(default="", description="Human-readable description")
    endpoint: str = Field(..., description="URL endpoint (e.g. '/webhooks/github')")
    source: Literal["github", "jira", "sentry", "slack", "gitlab", "custom"] = Field(
        default="custom", description="Webhook source type"
    )

    # Agent trigger configuration
    agent_trigger: AgentTriggerConfig = Field(
        default_factory=AgentTriggerConfig, description="How to trigger the agent"
    )

    # Target agent for routing
    target_agent: str = Field(
        default="brain", description="Default agent for routing tasks"
    )

    # Commands
    commands: List[CommandYamlConfig] = Field(
        default_factory=list, description="List of commands this webhook supports"
    )
    default_command: Optional[str] = Field(
        default=None, description="Default command when no specific command matched"
    )

    @model_validator(mode="after")
    def validate_commands_not_empty(self) -> "WebhookYamlConfig":
        """Commands list must not be empty."""
        if not self.commands:
            raise ValueError(
                "commands list cannot be empty - at least one command is required"
            )

        # Check for duplicate command names
        command_names = [cmd.name for cmd in self.commands]
        if len(command_names) != len(set(command_names)):
            duplicates = [
                name for name in command_names if command_names.count(name) > 1
            ]
            raise ValueError(
                f"Duplicate command names found: {', '.join(set(duplicates))}"
            )

        # Check that default_command exists in commands
        if self.default_command and self.default_command not in command_names:
            raise ValueError(
                f"default_command '{self.default_command}' not found in commands list"
            )

        return self

    # Security
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security configuration"
    )

    def to_webhook_config(self) -> "WebhookConfig":
        """Convert to WebhookConfig model."""
        return WebhookConfig(
            name=self.name,
            endpoint=self.endpoint,
            source=self.source,
            description=self.description,
            target_agent=self.target_agent,
            command_prefix=self.agent_trigger.prefix,
            commands=[cmd.to_webhook_command() for cmd in self.commands],
            default_command=self.default_command,
            requires_signature=self.security.requires_signature,
            signature_header=self.security.signature_header,
            secret_env_var=self.security.secret_env_var,
            is_builtin=True,
        )

    @classmethod
    def from_yaml_file(cls, file_path: Path) -> "WebhookYamlConfig":
        """Load configuration from a YAML file."""
        import yaml

        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


# =============================================================================
# SKILL MODEL
# =============================================================================


class SkillConfig(BaseModel):
    """Skill configuration."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    target: str = Field(..., description="'brain' or agent name")
    description: str = Field(default="")
    skill_path: Path = Field(...)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Target must be 'brain' or valid agent name."""
        if v != "brain" and not v.strip():
            raise ValueError("target must be 'brain' or a valid agent name")
        return v


# =============================================================================
# CREDENTIAL MODEL
# =============================================================================


class ClaudeCredentials(BaseModel):
    """Claude authentication credentials."""

    model_config = ConfigDict(validate_assignment=True)

    access_token: str = Field(..., min_length=10)
    refresh_token: str = Field(..., min_length=10)
    expires_at: int = Field(..., description="Expiry timestamp in milliseconds")
    token_type: str = Field(default="Bearer")
    account_id: Optional[str] = None

    @classmethod
    def normalize_credentials_data(cls, creds_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize credentials data from either format:
        1. Direct format: {"access_token": "...", "refresh_token": "...", ...}
        2. Wrapped format: {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...", ...}}

        Returns normalized dict with snake_case keys.
        """
        # Handle wrapped format with claudeAiOauth
        if "claudeAiOauth" in creds_data:
            oauth_data = creds_data["claudeAiOauth"]
            # Convert camelCase to snake_case for ClaudeCredentials model
            return {
                "access_token": oauth_data.get("accessToken")
                or oauth_data.get("access_token"),
                "refresh_token": oauth_data.get("refreshToken")
                or oauth_data.get("refresh_token"),
                "expires_at": oauth_data.get("expiresAt")
                or oauth_data.get("expires_at"),
                "token_type": oauth_data.get("tokenType", "Bearer"),
                "account_id": oauth_data.get("accountId")
                or oauth_data.get("account_id"),
            }

        # Already in direct format, return as-is
        return creds_data

    @classmethod
    def from_dict(cls, creds_data: Dict[str, Any]) -> "ClaudeCredentials":
        """Create ClaudeCredentials from dict, handling both formats."""
        normalized = cls.normalize_credentials_data(creds_data)
        return cls(**normalized)

    @property
    def user_id(self) -> Optional[str]:
        """Alias for account_id to maintain backward compatibility."""
        return self.account_id

    @property
    def expires_at_datetime(self) -> datetime:
        """Convert to datetime."""
        return datetime.fromtimestamp(self.expires_at / 1000, tz=timezone.utc)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at_datetime

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (< 30 min left)."""
        remaining = (
            self.expires_at_datetime - datetime.now(timezone.utc)
        ).total_seconds()
        return remaining < 1800  # 30 minutes

    def get_status(self) -> AuthStatus:
        """Get current auth status."""
        if self.is_expired:
            return AuthStatus.EXPIRED
        if self.needs_refresh:
            return AuthStatus.REFRESH_NEEDED
        return AuthStatus.VALID


# =============================================================================
# WEBSOCKET MESSAGE MODELS
# =============================================================================


class WebSocketMessage(BaseModel):
    """Base WebSocket message."""

    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskCreatedMessage(WebSocketMessage):
    """Task created event."""

    type: Literal["task.created"] = "task.created"
    task_id: str
    agent: str
    status: TaskStatus


class TaskOutputMessage(WebSocketMessage):
    """Task output chunk event."""

    type: Literal["task.output"] = "task.output"
    task_id: str
    chunk: str


class TaskMetricsMessage(WebSocketMessage):
    """Task metrics update event."""

    type: Literal["task.metrics"] = "task.metrics"
    task_id: str
    cost_usd: float
    tokens: int
    duration_seconds: float


class TaskCompletedMessage(WebSocketMessage):
    """Task completed event."""

    type: Literal["task.completed"] = "task.completed"
    task_id: str
    result: str
    cost_usd: float


class TaskFailedMessage(WebSocketMessage):
    """Task failed event."""

    type: Literal["task.failed"] = "task.failed"
    task_id: str
    error: str


class UserInputMessage(WebSocketMessage):
    """User input to task."""

    type: Literal["task.input"] = "task.input"
    task_id: str
    message: str


class TaskStopMessage(WebSocketMessage):
    """Stop task command."""

    type: Literal["task.stop"] = "task.stop"
    task_id: str


class ChatMessage(WebSocketMessage):
    """Chat with Brain."""

    type: Literal["chat.message"] = "chat.message"
    message: str


class CLIStatusUpdateMessage(WebSocketMessage):
    """CLI status update event."""

    type: Literal["cli_status_update"] = "cli_status_update"
    session_id: Optional[str] = None  # None means broadcast to all
    active: bool


# Union type for all WebSocket messages
WSMessage = (
    TaskCreatedMessage
    | TaskOutputMessage
    | TaskMetricsMessage
    | TaskCompletedMessage
    | TaskFailedMessage
    | UserInputMessage
    | TaskStopMessage
    | ChatMessage
    | CLIStatusUpdateMessage
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""

    method: Literal["describe", "upload", "form"]
    description: Optional[str] = None  # For method="describe"
    file_content: Optional[str] = None  # For method="upload"
    form_data: Optional[Dict[str, Any]] = None  # For method="form"

    @model_validator(mode="after")
    def validate_method_data(self) -> "CreateWebhookRequest":
        """Ensure correct data for method."""
        if self.method == "describe" and not self.description:
            raise ValueError("description required for method='describe'")
        if self.method == "upload" and not self.file_content:
            raise ValueError("file_content required for method='upload'")
        if self.method == "form" and not self.form_data:
            raise ValueError("form_data required for method='form'")
        return self


class CreateAgentRequest(BaseModel):
    """Request to create a sub-agent."""

    method: Literal["describe", "upload", "form"]
    description: Optional[str] = None
    folder_content: Optional[Dict[str, str]] = None  # filename -> content
    form_data: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_method_data(self) -> "CreateAgentRequest":
        """Ensure correct data for method."""
        if self.method == "describe" and not self.description:
            raise ValueError("description required for method='describe'")
        if self.method == "upload" and not self.folder_content:
            raise ValueError("folder_content required for method='upload'")
        if self.method == "form" and not self.form_data:
            raise ValueError("form_data required for method='form'")
        return self


class UploadCredentialsRequest(BaseModel):
    """Request to upload credentials."""

    credentials: ClaudeCredentials


class APIResponse(BaseModel):
    """Standard API response."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
