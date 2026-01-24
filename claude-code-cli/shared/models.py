"""Pydantic models for the AI Agent System.

All data models are consolidated here. No separate types.py needed.
"""

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field as dataclass_field
from typing import Optional, List, Dict, Any, Literal, Union, Callable, Awaitable

from pydantic import BaseModel, Field

from .enums import (
    TaskStatus,
    TaskSource,
    RiskLevel,
    TokenStatus,
    CommandType,
    Platform,
    GitOperation,
    TestFramework,
)


# =============================================================================
# CONFIGURATION MODELS (Frozen dataclasses for immutable config)
# =============================================================================

@dataclass(frozen=True)
class BotConfiguration:
    """Configuration for bot behavior."""
    tags: List[str]
    name: str
    emoji: str
    github_username: str
    jira_username: str
    slack_user_id: str


@dataclass(frozen=True)
class QueueConfiguration:
    """Configuration for Redis queues."""
    planning_queue: str
    execution_queue: str
    priority_queue: str


@dataclass(frozen=True)
class TimeoutConfiguration:
    """Timeout configurations in seconds."""
    claude_code: int
    git_clone: int
    test_run: int
    webhook_response: int


# =============================================================================
# OAUTH MODELS
# =============================================================================

@dataclass
class OAuthCredentials:
    """OAuth credentials structure."""
    access_token: str
    refresh_token: str
    expires_at: int  # milliseconds
    token_type: str = "Bearer"
    scope: str = ""

    @property
    def expires_at_datetime(self) -> datetime:
        """Convert milliseconds to datetime."""
        return datetime.fromtimestamp(self.expires_at / 1000)

    @property
    def minutes_until_expiry(self) -> float:
        """Minutes until token expires."""
        now = datetime.now()
        expiry = self.expires_at_datetime
        delta = expiry - now
        return delta.total_seconds() / 60

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.minutes_until_expiry <= 0

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (<30 min left)."""
        return self.minutes_until_expiry < 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "expiresAt": self.expires_at,
            "tokenType": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthCredentials":
        """Create from dictionary."""
        return cls(
            access_token=data.get("accessToken", ""),
            refresh_token=data.get("refreshToken", ""),
            expires_at=data.get("expiresAt", 0),
            token_type=data.get("tokenType", "Bearer"),
            scope=data.get("scope", ""),
        )


@dataclass
class TokenRefreshResult:
    """Result of a token refresh operation."""
    success: bool
    credentials: Optional[OAuthCredentials] = None
    error: Optional[str] = None
    status: TokenStatus = TokenStatus.UNKNOWN


# =============================================================================
# TASK MODELS (Pydantic for validation)
# =============================================================================

class BaseTask(BaseModel):
    """Base task with common fields."""
    task_id: str = Field(default_factory=lambda: f"task-{datetime.now().timestamp()}")
    source: TaskSource
    status: TaskStatus = TaskStatus.QUEUED
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata and metrics
    error: Optional[str] = None
    retry_count: int = 0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    duration_seconds: float = 0.0
    
    # Workflow
    improvement_request: Optional[str] = Field(None, description="Instructions for improving the plan/code")
    
    # External Links
    pr_url: Optional[str] = Field(None, description="GitHub PR URL")
    jira_url: Optional[str] = Field(None, description="Jira Issue URL")
    slack_url: Optional[str] = Field(None, description="Slack Thread/Message URL")
    repository_url: Optional[str] = Field(None, description="GitHub Repository URL")
    
    # Context
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class JiraTask(BaseTask):
    """Task from Jira webhook."""
    source: Literal[TaskSource.JIRA] = TaskSource.JIRA
    action: Literal["enrich", "fix", "approve"]
    issue_key: str
    description: str = ""
    full_description: str = ""
    sentry_issue_id: Optional[str] = None
    repository: Optional[str] = None


class SentryTask(BaseTask):
    """Task from Sentry webhook."""
    source: Literal[TaskSource.SENTRY] = TaskSource.SENTRY
    sentry_issue_id: str
    description: str
    repository: str


class GitHubTask(BaseTask):
    """Task from GitHub webhook."""
    source: Literal[TaskSource.GITHUB] = TaskSource.GITHUB
    repository: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    comment: Optional[str] = None
    action: Optional[str] = None


class SlackTask(BaseTask):
    """Task from Slack."""
    source: Literal[TaskSource.SLACK] = TaskSource.SLACK
    channel: str
    user: str
    text: str
    thread_ts: Optional[str] = None


# Union type for queue operations
AnyTask = Union[JiraTask, SentryTask, GitHubTask, SlackTask]


# =============================================================================
# GIT MODELS
# =============================================================================

@dataclass
class GitRepository:
    """A Git repository."""
    owner: str
    name: str
    full_name: str
    clone_url: str
    default_branch: str = "main"

    @classmethod
    def from_full_name(cls, full_name: str) -> "GitRepository":
        """Create from full_name (owner/repo)."""
        parts = full_name.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid repository name: {full_name}")
        owner, name = parts
        return cls(
            owner=owner,
            name=name,
            full_name=full_name,
            clone_url=f"https://github.com/{full_name}.git",
        )


@dataclass
class GitOperationResult:
    """Result of a Git operation."""
    operation: GitOperation
    success: bool
    output: str
    error: Optional[str] = None
    commit_sha: Optional[str] = None


# =============================================================================
# TEST MODELS
# =============================================================================

@dataclass
class TestResult:
    """Result of running tests."""
    framework: TestFramework
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    output: str
    failures: List[Dict[str, str]] = dataclass_field(default_factory=list)


@dataclass
class LintResult:
    """Result of running linter."""
    passed: bool
    error_count: int
    warning_count: int
    output: str
    fixable: int = 0


# =============================================================================
# CLAUDE CODE MODELS
# =============================================================================

@dataclass
class ClaudeCodeResult:
    """Result from Claude Code CLI execution."""
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: Optional[int] = None
    pr_url: Optional[str] = None
    return_code: int = 0


# =============================================================================
# COMMAND MODELS
# =============================================================================

@dataclass
class CommandParameter:
    """A parameter for a command."""
    name: str
    param_type: str
    required: bool
    description: str
    default: Optional[Any] = None


@dataclass
class CommandDefinition:
    """Definition of a bot command."""
    name: str
    aliases: List[str]
    description: str
    usage: str
    examples: List[str]
    parameters: List[CommandParameter]
    handler: str
    platforms: List[Platform]
    response_template: Optional[str] = None


@dataclass
class ParsedCommand:
    """A parsed command from user input."""
    command_type: CommandType
    command_name: str
    definition: Optional[CommandDefinition]
    args: List[str]
    raw_text: str
    platform: Platform
    context: Dict[str, Any]


@dataclass
class CommandResult:
    """Result of executing a command."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    should_reply: bool = True
    reaction: Optional[str] = None
