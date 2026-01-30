import structlog

from ..base import BaseAgent
from ..models import AgentTask, AgentContext, AgentResult
from ..executor import ExecutorAgent

logger = structlog.get_logger()


class JiraWorkflowAgent(BaseAgent):
    def __init__(self, executor: ExecutorAgent) -> None:
        super().__init__(
            agent_id="jira_workflow",
            agent_type="workflow",
        )
        self.executor = executor

    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        if task.provider != "jira":
            return False

        required_metadata = ["issue_key", "project_key"]
        for key in required_metadata:
            if key not in task.source_metadata:
                self.logger.warning(
                    "jira_workflow_missing_metadata",
                    task_id=task.task_id,
                    missing_key=key,
                )
                return False

        return True

    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        if "comment" in task.event_type:
            return await self._handle_comment(task, context)
        elif "created" in task.event_type:
            return await self._handle_issue_created(task, context)
        else:
            return await self.executor.execute(task, context)

    async def _handle_comment(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "jira_comment",
            task_id=task.task_id,
            issue_key=task.source_metadata.get("issue_key"),
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "jira_comment",
                "issue_key": task.source_metadata.get("issue_key", ""),
                "comment_body": task.source_metadata.get("comment_body", ""),
            },
        )

        return await self.executor.execute(task, enhanced_context)

    async def _handle_issue_created(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "jira_issue_created",
            task_id=task.task_id,
            issue_key=task.source_metadata.get("issue_key"),
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "jira_issue_analysis",
                "issue_key": task.source_metadata.get("issue_key", ""),
                "summary": task.source_metadata.get("summary", ""),
                "description": task.source_metadata.get("description", ""),
                "priority": task.source_metadata.get("priority", ""),
            },
        )

        return await self.executor.execute(task, enhanced_context)
