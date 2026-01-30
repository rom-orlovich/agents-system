import structlog

from ..base import BaseAgent
from ..models import AgentTask, AgentContext, AgentResult
from ..executor import ExecutorAgent

logger = structlog.get_logger()


class GitHubWorkflowAgent(BaseAgent):
    def __init__(self, executor: ExecutorAgent) -> None:
        super().__init__(
            agent_id="github_workflow",
            agent_type="workflow",
        )
        self.executor = executor

    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        if task.provider != "github":
            return False

        required_metadata = ["repo"]
        for key in required_metadata:
            if key not in task.source_metadata:
                self.logger.warning(
                    "github_workflow_missing_metadata",
                    task_id=task.task_id,
                    missing_key=key,
                )
                return False

        return True

    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        if task.event_type == "pull_request.opened":
            return await self._handle_pr_review(task, context)
        elif "comment" in task.event_type:
            return await self._handle_comment(task, context)
        elif "issue" in task.event_type:
            return await self._handle_issue(task, context)
        else:
            return await self.executor.execute(task, context)

    async def _handle_pr_review(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "github_pr_review",
            task_id=task.task_id,
            pr_number=task.source_metadata.get("pr_number"),
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "pr_review",
                "pr_number": task.source_metadata.get("pr_number", ""),
                "pr_title": task.source_metadata.get("pr_title", ""),
            },
        )

        return await self.executor.execute(task, enhanced_context)

    async def _handle_comment(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "github_comment",
            task_id=task.task_id,
            pr_number=task.source_metadata.get("pr_number"),
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "comment_response",
                "comment_body": task.source_metadata.get("comment_body", ""),
            },
        )

        return await self.executor.execute(task, enhanced_context)

    async def _handle_issue(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        self.logger.info(
            "github_issue",
            task_id=task.task_id,
        )

        enhanced_context = AgentContext(
            task=task,
            conversation_history=context.conversation_history,
            repository_path=context.repository_path,
            additional_context={
                **context.additional_context,
                "workflow_type": "issue_response",
            },
        )

        return await self.executor.execute(task, enhanced_context)
