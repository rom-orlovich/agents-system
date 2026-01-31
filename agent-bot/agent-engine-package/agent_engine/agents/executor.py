from .base import AgentContext, AgentResult, AgentType, BaseAgent

EXECUTOR_PROMPT = """You are a code executor agent. Your task is to implement the solution based on the plan.

Task ID: {task_id}
Repository: {repository}
Branch: {branch}

## Implementation Plan
{plan}

## Instructions
1. Follow TDD workflow: Red → Green → Refactor
2. Write failing tests first
3. Implement minimal code to pass
4. Refactor while keeping tests green
5. Commit changes with descriptive messages

## Constraints
- Maximum 300 lines per file
- No comments in code - self-documenting only
- Use async/await for I/O operations
- Use Pydantic with strict=True
- Use structured logging

Execute the implementation now.
"""


class ExecutorAgent(BaseAgent):
    agent_type = AgentType.EXECUTOR

    def can_handle(self, context: AgentContext) -> bool:
        return context.metadata.get("phase") == "execution"

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("executor_starting", task_id=context.task_id)

        plan = context.metadata.get("plan", "No plan provided")
        working_dir = self._get_working_dir(context)

        prompt = EXECUTOR_PROMPT.format(
            task_id=context.task_id,
            repository=context.repository or "unknown",
            branch=context.branch or "main",
            plan=plan,
        )

        result = await self._execute_cli(prompt, working_dir)

        if not result.get("success", False):
            return AgentResult(
                success=False,
                output=result.get("output", "Execution failed"),
                agent_type=self.agent_type,
                error=result.get("error"),
                next_agent=None,
                should_respond=True,
            )

        return AgentResult(
            success=True,
            output=result.get("output", ""),
            agent_type=self.agent_type,
            next_agent=AgentType.VERIFIER,
            artifacts={
                "files_changed": result.get("files_changed", []),
                "commits": result.get("commits", []),
            },
            should_respond=False,
        )

    def _get_working_dir(self, context: AgentContext) -> str:
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"
