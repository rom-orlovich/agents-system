class JiraClientError(Exception):
    pass


class JiraAuthenticationError(JiraClientError):
    pass


class JiraNotFoundError(JiraClientError):
    pass


class JiraValidationError(JiraClientError):
    pass


class JiraRateLimitError(JiraClientError):
    pass


class JiraServerError(JiraClientError):
    pass
