from .base import AgentContext, AgentResult, AgentType, BaseAgent, TaskSource

GITHUB_ISSUE_PROMPT = """You are a GitHub issue handler agent. Analyze and respond to GitHub issues.

Task ID: {task_id}
Repository: {repository}
Issue: #{issue_number}

## Issue Details
Title: {title}
Body: {body}
Labels: {labels}
Author: {author}

## Instructions
1. Analyze the issue to understand the request
2. If it's a bug report, investigate the codebase
3. If it's a feature request, assess feasibility
4. If it requires code changes, create an implementation plan
5. Provide a helpful response

## Response Guidelines
- Be concise and professional
- Acknowledge the issue
- Provide next steps or ask clarifying questions
- If code changes needed, indicate that a plan will be created
"""


class GitHubIssueHandlerAgent(BaseAgent):
    agent_type = AgentType.GITHUB_ISSUE

    def can_handle(self, context: AgentContext) -> bool:
        return (
            context.source == TaskSource.GITHUB
            and context.event_type in ("issues", "issue_comment")
        )

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("github_issue_processing", task_id=context.task_id)

        issue = context.payload.get("issue", {})
        working_dir = self._get_working_dir(context)

        prompt = GITHUB_ISSUE_PROMPT.format(
            task_id=context.task_id,
            repository=context.repository or "unknown",
            issue_number=issue.get("number", "unknown"),
            title=issue.get("title", "No title"),
            body=issue.get("body", "No description"),
            labels=", ".join(l.get("name", "") for l in issue.get("labels", [])),
            author=issue.get("user", {}).get("login", "unknown"),
        )

        result = await self._execute_cli(prompt, working_dir)

        needs_implementation = self._check_needs_implementation(issue)

        return AgentResult(
            success=result.get("success", False),
            output=result.get("output", ""),
            agent_type=self.agent_type,
            next_agent=AgentType.PLANNING if needs_implementation else None,
            artifacts={
                "issue_number": issue.get("number"),
                "needs_implementation": needs_implementation,
            },
            should_respond=True,
            response_channel=f"github:issue:{issue.get('number')}",
        )

    def _get_working_dir(self, context: AgentContext) -> str:
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"

    def _check_needs_implementation(self, issue: dict) -> bool:
        labels = [l.get("name", "").lower() for l in issue.get("labels", [])]
        implementation_labels = ["ai-fix", "enhancement", "bug", "feature"]
        return any(label in labels for label in implementation_labels)
