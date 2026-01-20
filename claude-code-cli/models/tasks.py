"""Task models for the AI Agent System."""

from datetime import datetime
from typing import Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field

from types.enums import TaskStatus, TaskSource


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
