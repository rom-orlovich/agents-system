from datetime import datetime
import uuid
import structlog

from .base import BaseAgent
from .models import (
    AgentTask,
    AgentContext,
    AgentResult,
    ExecutionPlan,
    PlanStep,
)

logger = structlog.get_logger()


class BrainAgent(BaseAgent):
    def __init__(
        self,
        planning_agent: BaseAgent | None = None,
        executor_agent: BaseAgent | None = None,
    ) -> None:
        super().__init__(agent_id="brain", agent_type="orchestrator")
        self.planning_agent = planning_agent
        self.executor_agent = executor_agent

    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        if not task.task_id or not task.provider:
            return False
        if not task.input_message:
            return False
        return True

    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        start_time = datetime.now()

        task_type = await self._analyze_task_type(task)

        self.logger.info(
            "brain_task_analysis",
            task_id=task.task_id,
            task_type=task_type,
        )

        if self.executor_agent:
            result = await self.executor_agent.execute(task, context)
        else:
            result = await self._execute_direct(task, context)

        duration = (datetime.now() - start_time).total_seconds()

        result.duration_seconds = duration
        result.metadata["task_type"] = task_type
        result.metadata["orchestrated_by"] = "brain"

        return result

    async def _analyze_task_type(self, task: AgentTask) -> str:
        if task.provider == "github":
            if "review" in task.input_message.lower():
                return "code_review"
            if "fix" in task.input_message.lower():
                return "bug_fix"
            return "github_inquiry"

        if task.provider == "jira":
            if "analyze" in task.input_message.lower():
                return "issue_analysis"
            return "jira_inquiry"

        if task.provider == "slack":
            return "slack_inquiry"

        if task.provider == "sentry":
            return "error_investigation"

        return "generic"

    async def _execute_direct(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"Processed {task.event_type} for {task.provider}",
            model_used="direct",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            duration_seconds=0.0,
        )

    async def create_plan(self, task: AgentTask) -> ExecutionPlan:
        task_type = await self._analyze_task_type(task)

        steps: list[PlanStep] = []

        if task_type == "code_review":
            steps = [
                PlanStep(
                    step_id="step-1",
                    action="analyze",
                    description="Analyze PR changes",
                    agent_type="analyzer",
                ),
                PlanStep(
                    step_id="step-2",
                    action="verify",
                    description="Verify code quality",
                    agent_type="verifier",
                    dependencies=["step-1"],
                ),
                PlanStep(
                    step_id="step-3",
                    action="post",
                    description="Post review comments",
                    agent_type="poster",
                    dependencies=["step-2"],
                ),
            ]
        else:
            steps = [
                PlanStep(
                    step_id="step-1",
                    action="analyze",
                    description="Analyze task",
                    agent_type="analyzer",
                ),
                PlanStep(
                    step_id="step-2",
                    action="post",
                    description="Post result",
                    agent_type="poster",
                    dependencies=["step-1"],
                ),
            ]

        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            task_id=task.task_id,
            steps=steps,
            estimated_duration_seconds=len(steps) * 30.0,
        )
