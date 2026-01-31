from .base import (
    AgentContext,
    AgentResult,
    AgentType,
    BaseAgent,
    CLIExecutor,
    TaskSource,
)


class BrainAgent(BaseAgent):
    agent_type = AgentType.BRAIN

    def __init__(self, cli_executor: CLIExecutor):
        super().__init__(cli_executor)
        self._routing_rules = self._build_routing_rules()

    def _build_routing_rules(self) -> dict[tuple[TaskSource, str], AgentType]:
        return {
            (TaskSource.GITHUB, "issues"): AgentType.GITHUB_ISSUE,
            (TaskSource.GITHUB, "issue_comment"): AgentType.GITHUB_ISSUE,
            (TaskSource.GITHUB, "pull_request"): AgentType.GITHUB_PR,
            (TaskSource.GITHUB, "pull_request_review_comment"): AgentType.GITHUB_PR,
            (TaskSource.JIRA, "jira:issue_created"): AgentType.JIRA_CODE,
            (TaskSource.JIRA, "jira:issue_updated"): AgentType.JIRA_CODE,
            (TaskSource.SLACK, "app_mention"): AgentType.SLACK_INQUIRY,
            (TaskSource.SLACK, "message"): AgentType.SLACK_INQUIRY,
            (TaskSource.SENTRY, "issue.created"): AgentType.PLANNING,
            (TaskSource.SENTRY, "error.created"): AgentType.PLANNING,
        }

    def can_handle(self, context: AgentContext) -> bool:
        return True

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info(
            "brain_routing_task",
            source=context.source.value,
            event_type=context.event_type,
        )

        next_agent = self._route_to_agent(context)

        if next_agent is None:
            return AgentResult(
                success=False,
                output="Unable to route task to appropriate agent",
                agent_type=self.agent_type,
                error=f"Unknown event type: {context.event_type}",
                should_respond=False,
            )

        self._logger.info(
            "brain_routed_task",
            next_agent=next_agent.value,
        )

        return AgentResult(
            success=True,
            output=f"Routed to {next_agent.value} agent",
            agent_type=self.agent_type,
            next_agent=next_agent,
            should_respond=False,
        )

    def _route_to_agent(self, context: AgentContext) -> AgentType | None:
        key = (context.source, context.event_type)
        if key in self._routing_rules:
            return self._routing_rules[key]

        for (source, event_prefix), agent in self._routing_rules.items():
            if source == context.source and context.event_type.startswith(event_prefix):
                return agent

        if context.source == TaskSource.GITHUB:
            return AgentType.GITHUB_ISSUE
        if context.source == TaskSource.JIRA:
            return AgentType.JIRA_CODE
        if context.source == TaskSource.SLACK:
            return AgentType.SLACK_INQUIRY

        return AgentType.PLANNING
