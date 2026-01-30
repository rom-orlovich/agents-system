"""Slack client exceptions."""


class SlackAPIError(Exception):
    """Base exception for Slack API errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class SlackAuthError(SlackAPIError):
    """Slack authentication error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, error_code="not_authed")


class SlackNotFoundError(SlackAPIError):
    """Slack resource not found."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", error_code="channel_not_found")
