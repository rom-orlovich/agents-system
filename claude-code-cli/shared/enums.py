"""All enums for the AI Agent system.

This module contains all enumeration types used throughout the system.
Using enums ensures type safety and prevents typos in string comparisons.
"""

from enum import Enum
from typing import List


class TaskStatus(str, Enum):
    """Status of a task in the system.
    
    Inherits from str to allow JSON serialization and string comparison.
    """
    PENDING = "pending"
    DISCOVERING = "discovering"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    @classmethod
    def terminal_states(cls) -> List["TaskStatus"]:
        """States that indicate task completion."""
        return [cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.REJECTED]
    
    @classmethod
    def active_states(cls) -> List["TaskStatus"]:
        """States that indicate task is in progress."""
        return [cls.DISCOVERING, cls.PLANNING, cls.EXECUTING]


class TaskSource(str, Enum):
    """Source that triggered the task."""
    JIRA = "jira"
    GITHUB = "github"
    GITHUB_COMMENT = "github_comment"
    SLACK = "slack"
    SENTRY = "sentry"
    MANUAL = "manual"
    API = "api"


class TokenStatus(str, Enum):
    """Status of OAuth token."""
    VALID = "valid"                    # Token is valid for > 30 min
    NEEDS_REFRESH = "needs_refresh"    # Token valid but < 30 min left
    EXPIRED = "expired"                # Token has expired
    REFRESHED = "refreshed"            # Token was just refreshed
    REFRESH_FAILED = "refresh_failed"  # Refresh attempt failed
    NOT_FOUND = "not_found"            # No credentials file found
    INVALID = "invalid"                # Credentials file is invalid
    UNKNOWN = "unknown"


class CommandType(str, Enum):
    """Types of bot commands.
    
    Each command type maps to a handler in the CommandExecutor.
    """
    # Core commands
    APPROVE = "approve"
    REJECT = "reject"
    IMPROVE = "improve"
    STATUS = "status"
    HELP = "help"
    
    # Discovery commands
    DISCOVER = "discover"
    LIST_REPOS = "list_repos"
    LIST_FILES = "list_files"
    
    # Code understanding
    EXPLAIN = "explain"
    ASK = "ask"
    FIND = "find"
    DIFF = "diff"
    
    # CI/CD
    CI_STATUS = "ci_status"
    CI_LOGS = "ci_logs"
    RETRY_CI = "retry_ci"
    
    # PR management
    UPDATE_TITLE = "update_title"
    ADD_TESTS = "add_tests"
    FIX_LINT = "fix_lint"
    
    # Jira
    UPDATE_JIRA = "update_jira"
    LINK_PR = "link_pr"
    
    # Unknown/catch-all
    UNKNOWN = "unknown"


class Platform(str, Enum):
    """Platforms where commands can originate."""
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    API = "api"


class AgentType(str, Enum):
    """Types of agents in the system."""
    PLANNING = "planning"
    EXECUTOR = "executor"


class MCPServer(str, Enum):
    """Available MCP servers."""
    GITHUB = "github"
    ATLASSIAN = "atlassian"
    SENTRY = "sentry"
    FILESYSTEM = "filesystem"


class GitOperation(str, Enum):
    """Git operations that can be performed."""
    CLONE = "clone"
    PULL = "pull"
    CHECKOUT = "checkout"
    BRANCH = "branch"
    ADD = "add"
    COMMIT = "commit"
    PUSH = "push"
    STATUS = "status"
    DIFF = "diff"


class TestFramework(str, Enum):
    """Detected test frameworks."""
    NPM = "npm"
    PYTEST = "pytest"
    GO_TEST = "go_test"
    MAVEN = "maven"
    GRADLE = "gradle"
    UNKNOWN = "unknown"
