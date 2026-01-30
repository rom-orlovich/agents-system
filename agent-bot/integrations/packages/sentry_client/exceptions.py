"""Sentry client exceptions."""


class SentryAPIError(Exception):
    """Base exception for Sentry API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SentryAuthError(SentryAPIError):
    """Sentry authentication error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class SentryNotFoundError(SentryAPIError):
    """Sentry resource not found."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", status_code=404)
