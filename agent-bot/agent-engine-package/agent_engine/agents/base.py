from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    BRAIN = "brain"
    EXECUTOR = "executor"
    PLANNING = "planning"
    VERIFIER = "verifier"
    GITHUB_ISSUE = "github-issue-handler"
    GITHUB_PR = "github-pr-review"
    JIRA_CODE = "jira-code-plan"
    SLACK_INQUIRY = "slack-inquiry"
    SERVICE_INTEGRATOR = "service-integrator"


class TaskSource(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"
    INTERNAL = "internal"


@dataclass
class AgentContext:
    task_id: str
    source: TaskSource
    event_type: str
    payload: dict[str, Any]
    repository: str | None = None
    branch: str | None = None
    conversation_id: str | None = None
    parent_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    success: bool
    output: str
    agent_type: AgentType
    next_agent: AgentType | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    should_respond: bool = True
    response_channel: str | None = None


class CLIExecutor(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]: ...


class BaseAgent(ABC):
    agent_type: AgentType

    def __init__(self, cli_executor: CLIExecutor):
        self._cli = cli_executor
        self._logger = logger.bind(agent=self.agent_type.value)

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResult:
        pass

    @abstractmethod
    def can_handle(self, context: AgentContext) -> bool:
        pass

    def get_prompt_template(self) -> str:
        return ""

    async def _execute_cli(
        self,
        prompt: str,
        working_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        self._logger.info("executing_cli", working_dir=working_dir)
        result = await self._cli.execute(prompt, working_dir, timeout)
        self._logger.info(
            "cli_execution_complete",
            success=result.get("success", False),
        )
        return result

    def _build_prompt(self, context: AgentContext, template: str) -> str:
        return template.format(
            task_id=context.task_id,
            source=context.source.value,
            event_type=context.event_type,
            repository=context.repository or "unknown",
            branch=context.branch or "main",
            payload=context.payload,
        )
