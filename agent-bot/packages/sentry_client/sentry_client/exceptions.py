class SentryClientError(Exception):
    pass


class SentryAuthenticationError(SentryClientError):
    pass


class SentryNotFoundError(SentryClientError):
    pass


class SentryValidationError(SentryClientError):
    pass


class SentryRateLimitError(SentryClientError):
    pass


class SentryServerError(SentryClientError):
    pass
