from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class SkillType(str, Enum):
    DISCOVERY = "discovery"
    TESTING = "testing"
    CODE_REFACTORING = "code-refactoring"
    GITHUB_OPERATIONS = "github-operations"
    JIRA_OPERATIONS = "jira-operations"
    SLACK_OPERATIONS = "slack-operations"
    HUMAN_APPROVAL = "human-approval"
    VERIFICATION = "verification"
    WEBHOOK_MANAGEMENT = "webhook-management"


@dataclass
class SkillInput:
    action: str
    parameters: dict[str, Any]
    context: dict[str, Any]


@dataclass
class SkillOutput:
    success: bool
    result: Any
    error: str | None = None
    metadata: dict[str, Any] | None = None


class HTTPClient(Protocol):
    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]: ...
    async def post(self, url: str, **kwargs: Any) -> dict[str, Any]: ...
    async def put(self, url: str, **kwargs: Any) -> dict[str, Any]: ...
    async def delete(self, url: str, **kwargs: Any) -> dict[str, Any]: ...


class BaseSkill(ABC):
    skill_type: SkillType

    def __init__(self, http_client: HTTPClient):
        self._http = http_client
        self._logger = logger.bind(skill=self.skill_type.value)

    @abstractmethod
    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        pass

    @abstractmethod
    def get_available_actions(self) -> list[str]:
        pass
