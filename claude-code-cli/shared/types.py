"""Type definitions for the AI Agent system.

This module contains all dataclasses and TypedDicts used for type hints.
All types are explicitly defined for maintainability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, TypedDict
from pathlib import Path

from .enums import (
    TaskStatus, 
    TaskSource, 
    CommandType, 
    Platform,
    TestFramework, 
    GitOperation,
    TokenStatus,
)


# =============================================================================
# CONFIGURATION TYPES
# =============================================================================

@dataclass(frozen=True)
class BotConfiguration:
    """Configuration for bot behavior.
    
    Attributes:
        tags: List of trigger tags (e.g., ["@agent", "@claude"])
        name: Display name for the bot
        emoji: Emoji to use in messages
        github_username: Bot's GitHub username
        jira_username: Bot's Jira username
        slack_user_id: Bot's Slack user ID
    """
    tags: List[str]
    name: str
    emoji: str
    github_username: str
    jira_username: str
    slack_user_id: str


@dataclass(frozen=True)
class QueueConfiguration:
    """Configuration for Redis queues.
    
    Attributes:
        planning_queue: Name of planning queue
        execution_queue: Name of execution queue
        priority_queue: Name of priority queue
    """
    planning_queue: str
    execution_queue: str
    priority_queue: str


@dataclass(frozen=True)
class TimeoutConfiguration:
    """Timeout configurations in seconds.
    
    Attributes:
        claude_code: Timeout for Claude Code CLI
        git_clone: Timeout for git clone
        test_run: Timeout for test execution
        webhook_response: Timeout for webhook response
    """
    claude_code: int
    git_clone: int
    test_run: int
    webhook_response: int


# =============================================================================
# OAUTH TYPES
# =============================================================================

@dataclass
class OAuthCredentials:
    """OAuth credentials structure.
    
    Attributes:
        access_token: Current access token for API calls
        refresh_token: Token used to get new access tokens
        expires_at: Unix timestamp (milliseconds) when access_token expires
        token_type: Usually "Bearer"
        scope: OAuth scopes granted
    """
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
        """Check if token needs refresh (< 30 min left)."""
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
    """Result of a token refresh operation.
    
    Attributes:
        success: Whether refresh succeeded
        credentials: New credentials if success
        error: Error message if failed
        status: Current token status
    """
    success: bool
    credentials: Optional[OAuthCredentials] = None
    error: Optional[str] = None
    status: TokenStatus = TokenStatus.UNKNOWN


# =============================================================================
# TASK TYPES
# =============================================================================
# NOTE: The main Task model is defined in shared/models.py (Pydantic).
# TaskContext is kept here for lightweight context passing.

@dataclass
class TaskContext:
    """Context information for a task.
    
    Attributes:
        task_id: Unique task identifier
        repository: GitHub repository (owner/repo format)
        issue_key: Jira issue key (e.g., PROJ-123)
        pr_number: GitHub PR number
        pr_url: Full URL to the PR
        branch: Git branch name
        sentry_issue_id: Sentry issue ID if applicable
    """
    task_id: str
    repository: Optional[str] = None
    issue_key: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    branch: Optional[str] = None
    sentry_issue_id: Optional[str] = None


# =============================================================================
# COMMAND TYPES
# =============================================================================

@dataclass
class CommandParameter:
    """A parameter for a command.
    
    Attributes:
        name: Parameter name
        param_type: Expected type (string, number, boolean)
        required: Whether parameter is required
        description: What the parameter does
        default: Default value if not provided
    """
    name: str
    param_type: str
    required: bool
    description: str
    default: Optional[Any] = None


@dataclass
class CommandDefinition:
    """Definition of a bot command.
    
    Attributes:
        name: Command name
        aliases: Alternative names
        description: Full description
        usage: Usage syntax
        examples: Example usages
        parameters: List of parameters
        handler: Handler function name
        platforms: Where command is available
        response_template: Template for response
    """
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
    """A parsed command from user input.
    
    Attributes:
        command_type: Type of command
        command_name: Name of the command
        definition: Full command definition
        args: Extracted arguments
        raw_text: Original text after trigger
        platform: Where command came from
        context: Platform-specific context
    """
    command_type: CommandType
    command_name: str
    definition: Optional[CommandDefinition]
    args: List[str]
    raw_text: str
    platform: Platform
    context: Dict[str, Any]


@dataclass
class CommandResult:
    """Result of executing a command.
    
    Attributes:
        success: Whether command succeeded
        message: Human-readable message
        data: Additional structured data
        should_reply: Whether to post a reply
        reaction: Optional reaction to add (GitHub/Slack)
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    should_reply: bool = True
    reaction: Optional[str] = None


# =============================================================================
# GIT TYPES
# =============================================================================

@dataclass
class GitRepository:
    """A Git repository.
    
    Attributes:
        owner: Repository owner/org
        name: Repository name
        full_name: Full name (owner/name)
        clone_url: URL for cloning
        default_branch: Default branch name
    """
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
    """Result of a Git operation.
    
    Attributes:
        operation: Which operation was performed
        success: Whether it succeeded
        output: Command output
        error: Error message if failed
        commit_sha: New commit SHA if applicable
    """
    operation: GitOperation
    success: bool
    output: str
    error: Optional[str] = None
    commit_sha: Optional[str] = None


# =============================================================================
# TEST TYPES
# =============================================================================

@dataclass
class TestResult:
    """Result of running tests.
    
    Attributes:
        framework: Which test framework was used
        passed: Whether all tests passed
        total_tests: Total number of tests
        passed_tests: Number that passed
        failed_tests: Number that failed
        skipped_tests: Number skipped
        duration_seconds: How long tests took
        output: Full test output
        failures: Details of failures
    """
    framework: TestFramework
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    output: str
    failures: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class LintResult:
    """Result of running linter.
    
    Attributes:
        passed: Whether linting passed
        error_count: Number of errors
        warning_count: Number of warnings
        output: Full linter output
        fixable: Number of auto-fixable issues
    """
    passed: bool
    error_count: int
    warning_count: int
    output: str
    fixable: int = 0


# =============================================================================
# CLAUDE CODE TYPES
# =============================================================================

@dataclass
class ClaudeCodeResult:
    """Result from Claude Code CLI execution.
    
    Attributes:
        success: Whether execution succeeded
        output: Claude's response
        error: Error message if failed
        duration_seconds: How long it took
        tokens_used: Approximate token count
        pr_url: Extracted PR URL if created
    """
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: Optional[int] = None
    pr_url: Optional[str] = None


# =============================================================================
# WEBHOOK TYPES (TypedDict for JSON payloads)
# =============================================================================

class GitHubCommentContext(TypedDict):
    """Context from a GitHub comment webhook."""
    pr_number: int
    repository: str
    comment_id: int
    author: str
    pr_url: str
    task_id: Optional[str]


class JiraCommentContext(TypedDict):
    """Context from a Jira comment webhook."""
    issue_key: str
    comment_id: str
    project: str
    author: str
    task_id: Optional[str]


class SlackMessageContext(TypedDict):
    """Context from a Slack message."""
    channel: str
    thread_ts: Optional[str]
    user: str
    response_url: Optional[str]
