class SentryClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SentryAuthenticationError(SentryClientError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class SentryNotFoundError(SentryClientError):
    def __init__(self, resource: str, resource_id: str):
        message = f"{resource} with ID {resource_id} not found"
        super().__init__(message, status_code=404)


class SentryValidationError(SentryClientError):
    def __init__(self, field: str, reason: str):
        message = f"Validation failed for {field}: {reason}"
        super().__init__(message, status_code=400)


class SentryRateLimitError(SentryClientError):
    def __init__(self, retry_after: int | None = None):
        message = f"Rate limit exceeded{f', retry after {retry_after}s' if retry_after else ''}"
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class SentryServerError(SentryClientError):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)
