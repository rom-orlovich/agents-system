from datetime import datetime
from typing import Any
import structlog

from .base import BaseAgent
from .models import AgentTask, AgentContext, AgentResult

logger = structlog.get_logger()


class ExecutorAgent(BaseAgent):
    def __init__(self, cli_runner: Any) -> None:
        super().__init__(agent_id="executor", agent_type="executor")
        self.cli_runner = cli_runner

    async def validate_input(
        self, task: AgentTask, context: AgentContext
    ) -> bool:
        if not context.repository_path and task.provider == "github":
            self.logger.warning(
                "executor_missing_repo",
                task_id=task.task_id,
            )
            return False
        return True

    async def execute(
        self, task: AgentTask, context: AgentContext
    ) -> AgentResult:
        start_time = datetime.now()

        try:
            prompt = self._build_prompt(task, context)

            self.logger.info(
                "executor_running_cli",
                task_id=task.task_id,
                provider=task.provider,
            )

            cli_result = await self.cli_runner.run(
                prompt=prompt,
                working_directory=context.repository_path or "/tmp",
                environment_vars={},
            )

            duration = (datetime.now() - start_time).total_seconds()

            if cli_result.exit_code == 0:
                return AgentResult(
                    success=True,
                    output=cli_result.output,
                    model_used=cli_result.model_used,
                    input_tokens=cli_result.input_tokens,
                    output_tokens=cli_result.output_tokens,
                    cost_usd=self._calculate_cost(
                        cli_result.input_tokens,
                        cli_result.output_tokens,
                    ),
                    duration_seconds=duration,
                )
            else:
                return AgentResult(
                    success=False,
                    output=cli_result.output,
                    model_used=cli_result.model_used,
                    input_tokens=cli_result.input_tokens,
                    output_tokens=cli_result.output_tokens,
                    cost_usd=0.0,
                    duration_seconds=duration,
                    error=cli_result.error,
                )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                "executor_failed",
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
                duration_seconds=duration,
                error=str(e),
            )

    def _build_prompt(self, task: AgentTask, context: AgentContext) -> str:
        prompt_parts = []

        if context.conversation_history:
            prompt_parts.append("Previous conversation:")
            for msg in context.conversation_history[-5:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")

        if task.provider == "github":
            pr_number = task.source_metadata.get("pr_number")
            if pr_number:
                prompt_parts.append(
                    f"Review PR #{pr_number} in repository "
                    f"{task.source_metadata.get('repo', '')}"
                )

        if task.provider == "jira":
            issue_key = task.source_metadata.get("issue_key")
            if issue_key:
                prompt_parts.append(f"Analyze Jira issue {issue_key}")

        prompt_parts.append(f"Task: {task.input_message}")

        return "\n".join(prompt_parts)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost_per_million = 3.0
        output_cost_per_million = 15.0

        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million

        return input_cost + output_cost
