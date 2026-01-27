"""
Unified task factory for webhook task creation.

Consolidates create_github_task, create_jira_task, create_slack_task
into a single unified implementation.
"""

from domain.task_factory.factory import (
    WebhookTaskFactory,
    extract_metadata,
    validate_task_creation,
)

__all__ = [
    "WebhookTaskFactory",
    "extract_metadata",
    "validate_task_creation",
]
