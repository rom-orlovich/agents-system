from .base import AgentContext, AgentResult, AgentType, BaseAgent, TaskSource

GITHUB_PR_PROMPT = """You are a GitHub PR review agent. Review pull requests and handle comments.

Task ID: {task_id}
Repository: {repository}
PR: #{pr_number}

## PR Details
Title: {title}
Body: {body}
Author: {author}
Branch: {branch}
Base: {base}

## Comment (if applicable)
{comment}

## Instructions
1. If this is an approval request (@agent approve), prepare to merge
2. If this is a question, analyze the code and respond
3. If this is a review request, provide code review
4. Check for code quality, security, and best practices

## Response Guidelines
- Be constructive and helpful
- Point out specific issues with line numbers
- Suggest improvements with code examples
- Acknowledge good practices
"""


class GitHubPRReviewAgent(BaseAgent):
    agent_type = AgentType.GITHUB_PR

    def can_handle(self, context: AgentContext) -> bool:
        return (
            context.source == TaskSource.GITHUB
            and context.event_type in ("pull_request", "pull_request_review_comment")
        )

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("github_pr_processing", task_id=context.task_id)

        pr = context.payload.get("pull_request", {})
        comment = context.payload.get("comment", {})
        working_dir = self._get_working_dir(context)

        prompt = GITHUB_PR_PROMPT.format(
            task_id=context.task_id,
            repository=context.repository or "unknown",
            pr_number=pr.get("number", "unknown"),
            title=pr.get("title", "No title"),
            body=pr.get("body", "No description"),
            author=pr.get("user", {}).get("login", "unknown"),
            branch=pr.get("head", {}).get("ref", "unknown"),
            base=pr.get("base", {}).get("ref", "main"),
            comment=comment.get("body", "No comment"),
        )

        is_approval = self._is_approval_request(comment)

        result = await self._execute_cli(prompt, working_dir)

        return AgentResult(
            success=result.get("success", False),
            output=result.get("output", ""),
            agent_type=self.agent_type,
            next_agent=AgentType.EXECUTOR if is_approval else None,
            artifacts={
                "pr_number": pr.get("number"),
                "is_approval": is_approval,
                "review_type": "approval" if is_approval else "comment",
            },
            should_respond=True,
            response_channel=f"github:pr:{pr.get('number')}",
        )

    def _get_working_dir(self, context: AgentContext) -> str:
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"

    def _is_approval_request(self, comment: dict) -> bool:
        body = comment.get("body", "").lower()
        return "@agent approve" in body or "@bot approve" in body
