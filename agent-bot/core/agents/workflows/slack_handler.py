import structlog

from ..base import BaseAgent
from ..models import AgentTask, AgentContext, AgentResult
from ..executor import ExecutorAgent

logger = structlog.get_logger()


class SlackWorkflowAgent(BaseAgent):
    def __init__(self, executor: ExecutorAgent) -> None:
        super().__init__(
            agent_id="slack_workflow",
            agent_type="workflow",
        )
        self.executor = executor

    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        if task.provider != "slack":
            return False

        required_metadata = ["channel", "user", "ts"]
        for key in required_metadata:
            if key not in task.source_metadata:
                self.logger.warning(
                    "slack_workflow_missing_metadata",
                    task_id=task.task_id,
                    missing_key=key,
                )
                return False

        return True

    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        if task.event_type == "app_mention":
            return await self._handle_mention(task, context)
        elif task.event_type == "message":
            return await self._handle_message(task, context)
        else:
            return await self.executor.execute(task, context)

    async def _handle_mention(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "slack_mention",
            task_id=task.task_id,
            channel=task.source_metadata.get("channel"),
        )

        thread_ts = task.source_metadata.get("thread_ts")

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "slack_mention",
                "channel": task.source_metadata.get("channel", ""),
                "thread_ts": thread_ts or task.source_metadata.get("ts", ""),
                "is_thread": bool(thread_ts),
            },
        )

        return await self.executor.execute(task, enhanced_context)

    async def _handle_message(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "slack_message",
            task_id=task.task_id,
            channel=task.source_metadata.get("channel"),
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "slack_message",
                "channel": task.source_metadata.get("channel", ""),
                "user": task.source_metadata.get("user", ""),
            },
        )

        return await self.executor.execute(task, enhanced_context)
