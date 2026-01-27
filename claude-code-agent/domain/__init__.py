"""
Domain layer - pure domain models with no I/O dependencies.

This package contains:
- models/: Pydantic models for webhooks, tasks, routing, notifications
- services/: Pure domain services (text extraction, command matching)
- exceptions/: Custom exception hierarchy
- result/: Result types for error handling
"""

# Lazy imports to avoid circular dependencies
# Import from submodules directly when needed

__all__ = [
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
    "TaskNotification",
    "TaskSummary",
    # Base
    "WebhookSource",
    # Result types
    "Result",
    "Success",
    "Failure",
    # Exceptions
    "WebhookError",
    "WebhookValidationError",
    "WebhookAuthenticationError",
    "TaskCreationError",
    "ExternalServiceError",
]


def __getattr__(name: str):
    """Lazy import for domain modules."""
    if name in (
        "GitHubWebhookPayload",
        "JiraWebhookPayload",
        "SlackWebhookPayload",
        "TaskCompletionContext",
        "TaskCompletionResult",
        "RoutingMetadata",
        "PRRouting",
        "TaskNotification",
        "TaskSummary",
        "WebhookSource",
    ):
        from domain import models
        return getattr(models, name)

    if name in ("Result", "Success", "Failure"):
        from domain import result
        return getattr(result, name)

    if name in (
        "WebhookError",
        "WebhookValidationError",
        "WebhookAuthenticationError",
        "TaskCreationError",
        "ExternalServiceError",
    ):
        from domain import exceptions
        return getattr(exceptions, name)

    raise AttributeError(f"module 'domain' has no attribute '{name}'")
