from abc import ABC, abstractmethod
from typing import Protocol
import structlog

from .models import AgentTask, AgentContext, AgentResult

logger = structlog.get_logger()


class AgentProtocol(Protocol):
    async def process(self, task: AgentTask, context: AgentContext) -> AgentResult:
        ...


class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: str) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.logger = logger.bind(agent_id=agent_id, agent_type=agent_type)

    async def process(self, task: AgentTask, context: AgentContext) -> AgentResult:
        self.logger.info(
            "agent_processing_start",
            task_id=task.task_id,
            provider=task.provider,
        )

        try:
            validation_result = await self.validate_input(task, context)
            if not validation_result:
                return AgentResult(
                    success=False,
                    output="",
                    model_used="",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    duration_seconds=0.0,
                    error="Input validation failed",
                )

            result = await self.execute(task, context)

            self.logger.info(
                "agent_processing_complete",
                task_id=task.task_id,
                success=result.success,
            )

            return result

        except Exception as e:
            self.logger.error(
                "agent_processing_failed",
                task_id=task.task_id,
                error=str(e),
            )
            return AgentResult(
                success=False,
                output="",
                model_used="",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                duration_seconds=0.0,
                error=str(e),
            )

    @abstractmethod
    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        pass

    @abstractmethod
    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        pass
