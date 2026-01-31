from .base import AgentContext, AgentResult, AgentType, BaseAgent

SERVICE_INTEGRATOR_PROMPT = """You are a service integrator agent. Coordinate responses across platforms.

Task ID: {task_id}
Original Source: {source}
Response Channel: {response_channel}

## Task Result
Success: {success}
Output: {output}

## Instructions
1. Format the response appropriately for the target platform
2. Post updates to the original source
3. Create cross-references if needed (e.g., link Jira to GitHub)
4. Update task status in all relevant systems

## Platform-Specific Formatting
- GitHub: Use markdown with code blocks
- Jira: Use Jira markup
- Slack: Use Slack mrkdwn format
"""


class ServiceIntegratorAgent(BaseAgent):
    agent_type = AgentType.SERVICE_INTEGRATOR

    def can_handle(self, context: AgentContext) -> bool:
        return context.metadata.get("phase") == "integration"

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("integrating_response", task_id=context.task_id)

        previous_result = context.metadata.get("previous_result", {})
        response_channel = context.metadata.get("response_channel", "")

        prompt = SERVICE_INTEGRATOR_PROMPT.format(
            task_id=context.task_id,
            source=context.source.value,
            response_channel=response_channel,
            success=previous_result.get("success", False),
            output=previous_result.get("output", ""),
        )

        result = await self._execute_cli(prompt, "/app/repos/default")

        formatted_response = self._format_for_platform(
            response_channel,
            previous_result.get("output", ""),
        )

        return AgentResult(
            success=True,
            output=formatted_response,
            agent_type=self.agent_type,
            next_agent=None,
            artifacts={
                "response_posted": True,
                "channel": response_channel,
            },
            should_respond=True,
            response_channel=response_channel,
        )

    def _format_for_platform(self, channel: str, output: str) -> str:
        if channel.startswith("github:"):
            return self._format_github(output)
        if channel.startswith("jira:"):
            return self._format_jira(output)
        if channel.startswith("slack:"):
            return self._format_slack(output)
        return output

    def _format_github(self, output: str) -> str:
        return f"## Agent Response\n\n{output}\n\n---\n*Automated by Agent Bot*"

    def _format_jira(self, output: str) -> str:
        return f"h2. Agent Response\n\n{output}\n\n----\n_Automated by Agent Bot_"

    def _format_slack(self, output: str) -> str:
        return f"*Agent Response*\n\n{output}\n\n_Automated by Agent Bot_"
