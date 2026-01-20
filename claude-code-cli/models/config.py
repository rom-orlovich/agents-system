"""Configuration models."""

from dataclasses import dataclass
from typing import List


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
