"""GitHub client exceptions."""


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GitHubAuthError(GitHubAPIError):
    """GitHub authentication error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class GitHubNotFoundError(GitHubAPIError):
    """GitHub resource not found."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", status_code=404)


class GitHubRateLimitError(GitHubAPIError):
    """GitHub rate limit exceeded."""

    def __init__(self, reset_time: int) -> None:
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded. Resets at {reset_time}", status_code=429)
