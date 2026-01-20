"""Data models for the AI Agent System."""

# Task models
from .tasks import (
    BaseTask,
    JiraTask,
    SentryTask,
    GitHubTask,
    SlackTask,
    AnyTask,
)

# Auth models
from .auth import (
    OAuthCredentials,
    TokenRefreshResult,
)

# Git models
from .git import (
    GitRepository,
    GitOperationResult,
)

# Command models
from .commands import (
    CommandParameter,
    CommandDefinition,
    ParsedCommand,
    CommandResult,
)

# Result models
from .results import (
    TestResult,
    LintResult,
    ClaudeCodeResult,
)

# Configuration models
from .config import (
    BotConfiguration,
    QueueConfiguration,
    TimeoutConfiguration,
)

__all__ = [
    # Tasks
    "BaseTask",
    "JiraTask",
    "SentryTask",
    "GitHubTask",
    "SlackTask",
    "AnyTask",
    # Auth
    "OAuthCredentials",
    "TokenRefreshResult",
    # Git
    "GitRepository",
    "GitOperationResult",
    # Commands
    "CommandParameter",
    "CommandDefinition",
    "ParsedCommand",
    "CommandResult",
    # Results
    "TestResult",
    "LintResult",
    "ClaudeCodeResult",
    # Config
    "BotConfiguration",
    "QueueConfiguration",
    "TimeoutConfiguration",
]
