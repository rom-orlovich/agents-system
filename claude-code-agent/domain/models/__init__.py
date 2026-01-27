"""
Domain models - pure Pydantic models with validation.

No I/O dependencies - these are pure data structures with business rules.
"""

from domain.models.webhook_payload import (
    WebhookSource,
    GitHubWebhookPayload,
    JiraWebhookPayload,
    SlackWebhookPayload,
)
from domain.models.task_completion import (
    TaskCompletionContext,
    TaskCompletionResult,
)
from domain.models.routing import (
    RoutingMetadata,
    PRRouting,
)
from domain.models.notifications import (
    TaskSummary,
    TaskNotification,
)

__all__ = [
    # Webhook source
    "WebhookSource",
    # Webhook payloads
    "GitHubWebhookPayload",
    "JiraWebhookPayload",
    "SlackWebhookPayload",
    # Task completion
    "TaskCompletionContext",
    "TaskCompletionResult",
    # Routing
    "RoutingMetadata",
    "PRRouting",
    # Notifications
    "TaskSummary",
    "TaskNotification",
]
