from dataclasses import dataclass
from typing import Optional


@dataclass
class SlackErrorContext:
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    event_type: Optional[str] = None
    team_id: Optional[str] = None


class SlackValidationError(Exception):
    def __init__(self, message: str, context: Optional[SlackErrorContext] = None):
        super().__init__(message)
        self.context = context or SlackErrorContext()


class SlackProcessingError(Exception):
    def __init__(self, message: str, context: Optional[SlackErrorContext] = None):
        super().__init__(message)
        self.context = context or SlackErrorContext()


class SlackResponseError(Exception):
    def __init__(self, message: str, context: Optional[SlackErrorContext] = None):
        super().__init__(message)
        self.context = context or SlackErrorContext()
