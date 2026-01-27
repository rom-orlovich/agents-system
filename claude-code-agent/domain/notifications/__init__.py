"""
Unified notification service module.

Consolidates send_slack_notification from:
- github/utils.py (73 lines)
- jira/utils.py (238 lines)
- slack/utils.py (73 lines)

Provides:
- NotificationConfig: Configuration for notification channels
- NotificationBuilder: Builds Slack Block Kit blocks
- NotificationService: Sends notifications
- extract_task_summary: Extracts summary from task results
"""

from domain.notifications.config import NotificationConfig
from domain.notifications.builder import NotificationBuilder
from domain.notifications.service import NotificationService
from domain.notifications.summary import extract_task_summary

__all__ = [
    "NotificationConfig",
    "NotificationBuilder",
    "NotificationService",
    "extract_task_summary",
]
