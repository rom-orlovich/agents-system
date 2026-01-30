class SlackClientError(Exception):
    pass


class SlackAuthenticationError(SlackClientError):
    pass


class SlackNotFoundError(SlackClientError):
    pass


class SlackValidationError(SlackClientError):
    pass


class SlackRateLimitError(SlackClientError):
    pass


class SlackServerError(SlackClientError):
    pass
