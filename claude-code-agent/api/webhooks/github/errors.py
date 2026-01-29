from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubErrorContext:
    repo: Optional[str] = None
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    comment_id: Optional[int] = None
    task_id: Optional[str] = None
    event_type: Optional[str] = None


class GitHubValidationError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()


class GitHubProcessingError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()


class GitHubResponseError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()


class GitHubSignatureError(Exception):
    def __init__(self, message: str, context: Optional[GitHubErrorContext] = None):
        super().__init__(message)
        self.context = context or GitHubErrorContext()
