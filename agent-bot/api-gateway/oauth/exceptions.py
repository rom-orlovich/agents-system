class OAuthError(Exception):
    pass


class GitHubAuthenticationError(OAuthError):
    pass


class SlackAuthenticationError(OAuthError):
    pass


class JiraAuthenticationError(OAuthError):
    pass
