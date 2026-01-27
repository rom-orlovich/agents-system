"""
Custom exception hierarchy for webhook handling.

This module defines a structured exception hierarchy that:
- Distinguishes between different error types
- Carries context information for better error messages
- Supports determining if errors are recoverable
"""

from typing import Any, Dict, Optional


class WebhookError(Exception):
    """
    Base exception for all webhook-related errors.

    All webhook exceptions inherit from this class, allowing
    handlers to catch all webhook errors with a single except clause.
    """

    def __init__(
        self,
        message: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.recoverable = recoverable

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error": self.message,
            "error_type": type(self).__name__,
            "recoverable": self.recoverable,
            **self.context,
        }


class WebhookValidationError(WebhookError):
    """
    Exception raised when webhook payload validation fails.

    This includes:
    - Missing required fields
    - Invalid field values
    - Payload structure issues
    """

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        if expected:
            ctx["expected"] = expected
        if actual:
            ctx["actual"] = actual

        super().__init__(message, context=ctx, recoverable=False)
        self.field = field
        self.expected = expected
        self.actual = actual


class WebhookAuthenticationError(WebhookError):
    """
    Exception raised when webhook authentication fails.

    This includes:
    - Invalid signature
    - Missing signature when required
    - Secret not configured
    """

    def __init__(
        self,
        message: str,
        *,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if source:
            ctx["source"] = source

        super().__init__(message, context=ctx, recoverable=False)
        self.source = source


class TaskCreationError(WebhookError):
    """
    Exception raised when task creation fails.

    This includes:
    - Database errors during task creation
    - Redis queue errors
    - Invalid task parameters
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: Optional[str] = None,
        webhook_source: Optional[str] = None,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if task_id:
            ctx["task_id"] = task_id
        if webhook_source:
            ctx["webhook_source"] = webhook_source
        if command:
            ctx["command"] = command

        super().__init__(message, context=ctx, recoverable=True)
        self.task_id = task_id
        self.webhook_source = webhook_source
        self.command = command


class ExternalServiceError(WebhookError):
    """
    Exception raised when an external service call fails.

    This includes:
    - GitHub API errors
    - Jira API errors
    - Slack API errors
    - Rate limiting
    """

    def __init__(
        self,
        message: str,
        *,
        service: str,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        ctx["service"] = service
        if status_code:
            ctx["status_code"] = status_code

        # Rate limit errors are recoverable
        recoverable = status_code in (429, 502, 503, 504) if status_code else True

        super().__init__(message, context=ctx, recoverable=recoverable)
        self.service = service
        self.status_code = status_code


class CommandMatchError(WebhookError):
    """
    Exception raised when command matching fails.

    This includes:
    - No command found in text
    - Invalid command format
    - Unknown command
    """

    def __init__(
        self,
        message: str,
        *,
        command: Optional[str] = None,
        available_commands: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        if command:
            ctx["command"] = command
        if available_commands:
            ctx["available_commands"] = available_commands

        super().__init__(message, context=ctx, recoverable=False)
        self.command = command
        self.available_commands = available_commands


class TokenNotConfiguredError(WebhookError):
    """
    Exception raised when a required token is not configured.

    This is a configuration error that cannot be retried.
    """

    def __init__(
        self,
        token_name: str,
        *,
        env_var: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = f"{token_name} not configured"
        if env_var:
            message += f". Set {env_var} environment variable."

        ctx = context or {}
        ctx["token_name"] = token_name
        if env_var:
            ctx["env_var"] = env_var

        super().__init__(message, context=ctx, recoverable=False)
        self.token_name = token_name
        self.env_var = env_var


class RateLimitError(ExternalServiceError):
    """
    Exception raised when an API rate limit is hit.

    Includes retry-after information when available.
    """

    def __init__(
        self,
        service: str,
        *,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        message = f"{service} rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds."

        ctx = context or {}
        if retry_after:
            ctx["retry_after"] = retry_after

        super().__init__(message, service=service, status_code=429, context=ctx)
        self.retry_after = retry_after
