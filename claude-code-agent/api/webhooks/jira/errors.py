from dataclasses import dataclass
from typing import Optional


@dataclass
class JiraErrorContext:
    issue_key: Optional[str] = None
    comment_id: Optional[str] = None
    task_id: Optional[str] = None
    event_type: Optional[str] = None
    project_key: Optional[str] = None


class JiraValidationError(Exception):
    def __init__(self, message: str, context: Optional[JiraErrorContext] = None):
        super().__init__(message)
        self.context = context or JiraErrorContext()


class JiraProcessingError(Exception):
    def __init__(self, message: str, context: Optional[JiraErrorContext] = None):
        super().__init__(message)
        self.context = context or JiraErrorContext()


class JiraResponseError(Exception):
    def __init__(self, message: str, context: Optional[JiraErrorContext] = None):
        super().__init__(message)
        self.context = context or JiraErrorContext()
