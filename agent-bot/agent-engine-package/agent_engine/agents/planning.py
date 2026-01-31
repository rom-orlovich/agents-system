from .base import AgentContext, AgentResult, AgentType, BaseAgent

PLANNING_PROMPT = """You are a planning agent. Your task is to analyze the request and create an implementation plan.

Task ID: {task_id}
Source: {source}
Repository: {repository}

## Request
{request}

## Instructions
1. Analyze the codebase to understand the current structure
2. Identify relevant files and dependencies
3. Create a step-by-step implementation plan
4. Consider edge cases and error handling
5. Estimate complexity and identify risks

## Output Format
Create a detailed PLAN.md with:
- Summary of changes
- Files to modify/create
- Step-by-step implementation tasks
- Testing strategy
- Rollback plan

Generate the implementation plan now.
"""


class PlanningAgent(BaseAgent):
    agent_type = AgentType.PLANNING

    def can_handle(self, context: AgentContext) -> bool:
        return context.metadata.get("phase") in ("planning", None)

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("planning_starting", task_id=context.task_id)

        request = self._extract_request(context)
        working_dir = self._get_working_dir(context)

        prompt = PLANNING_PROMPT.format(
            task_id=context.task_id,
            source=context.source.value,
            repository=context.repository or "unknown",
            request=request,
        )

        result = await self._execute_cli(prompt, working_dir)

        if not result.get("success", False):
            return AgentResult(
                success=False,
                output=result.get("output", "Planning failed"),
                agent_type=self.agent_type,
                error=result.get("error"),
                should_respond=True,
            )

        plan = result.get("output", "")

        return AgentResult(
            success=True,
            output=plan,
            agent_type=self.agent_type,
            next_agent=AgentType.EXECUTOR,
            artifacts={"plan": plan},
            should_respond=True,
            response_channel=self._get_response_channel(context),
        )

    def _extract_request(self, context: AgentContext) -> str:
        payload = context.payload
        if "issue" in payload:
            issue = payload["issue"]
            return f"Title: {issue.get('title', '')}\n\nBody: {issue.get('body', '')}"
        if "comment" in payload:
            return payload["comment"].get("body", "")
        if "message" in payload:
            return payload["message"].get("text", "")
        return str(payload)

    def _get_working_dir(self, context: AgentContext) -> str:
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"

    def _get_response_channel(self, context: AgentContext) -> str | None:
        payload = context.payload
        if "issue" in payload:
            return f"github:issue:{payload['issue'].get('number')}"
        if "pull_request" in payload:
            return f"github:pr:{payload['pull_request'].get('number')}"
        if "channel" in payload:
            return f"slack:{payload['channel']}"
        return None
