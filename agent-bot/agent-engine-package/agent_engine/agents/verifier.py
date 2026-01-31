from .base import AgentContext, AgentResult, AgentType, BaseAgent

VERIFIER_PROMPT = """You are a verification agent. Your task is to verify the implementation.

Task ID: {task_id}
Repository: {repository}
Branch: {branch}

## Changes Made
{changes}

## Verification Steps
1. Run all unit tests
2. Run integration tests if available
3. Check code quality (linting, type checking)
4. Verify no security vulnerabilities introduced
5. Check file sizes (max 300 lines)
6. Verify no secrets in code

## Commands to Run
- pytest -v
- mypy . --strict
- ruff check .

Report any issues found.
"""


class VerifierAgent(BaseAgent):
    agent_type = AgentType.VERIFIER

    def can_handle(self, context: AgentContext) -> bool:
        return context.metadata.get("phase") == "verification"

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("verifier_starting", task_id=context.task_id)

        changes = context.metadata.get("changes", "No changes recorded")
        working_dir = self._get_working_dir(context)

        prompt = VERIFIER_PROMPT.format(
            task_id=context.task_id,
            repository=context.repository or "unknown",
            branch=context.branch or "main",
            changes=changes,
        )

        result = await self._execute_cli(prompt, working_dir)

        verification_passed = self._check_verification_result(result)

        if not verification_passed:
            return AgentResult(
                success=False,
                output=result.get("output", "Verification failed"),
                agent_type=self.agent_type,
                error="Verification checks failed",
                next_agent=AgentType.EXECUTOR,
                artifacts={"issues": result.get("issues", [])},
                should_respond=True,
            )

        return AgentResult(
            success=True,
            output="All verification checks passed",
            agent_type=self.agent_type,
            next_agent=None,
            artifacts={
                "test_results": result.get("test_results", {}),
                "coverage": result.get("coverage", 0),
            },
            should_respond=True,
        )

    def _get_working_dir(self, context: AgentContext) -> str:
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"

    def _check_verification_result(self, result: dict) -> bool:
        if not result.get("success", False):
            return False

        output = result.get("output", "").lower()
        failure_indicators = [
            "failed",
            "error",
            "exception",
            "traceback",
        ]
        return not any(indicator in output for indicator in failure_indicators)
