from .base import AgentContext, AgentResult, AgentType, BaseAgent, TaskSource

JIRA_CODE_PROMPT = """You are a Jira code planning agent. Handle Jira tickets that require code changes.

Task ID: {task_id}
Issue Key: {issue_key}
Project: {project}

## Issue Details
Summary: {summary}
Description: {description}
Type: {issue_type}
Priority: {priority}
Labels: {labels}

## Instructions
1. Analyze the Jira ticket requirements
2. Identify the affected repository and codebase
3. Create a detailed implementation plan
4. Break down into subtasks if needed
5. Estimate effort and complexity

## Response Guidelines
- Acknowledge the ticket
- Provide implementation approach
- List acceptance criteria
- Identify dependencies and risks
"""


class JiraCodePlanAgent(BaseAgent):
    agent_type = AgentType.JIRA_CODE

    def can_handle(self, context: AgentContext) -> bool:
        if context.source != TaskSource.JIRA:
            return False
        issue = context.payload.get("issue", {})
        labels = [l.lower() for l in issue.get("fields", {}).get("labels", [])]
        return "ai-fix" in labels or "code-change" in labels

    async def process(self, context: AgentContext) -> AgentResult:
        self._logger.info("jira_processing", task_id=context.task_id)

        issue = context.payload.get("issue", {})
        fields = issue.get("fields", {})
        working_dir = self._get_working_dir(context, fields)

        prompt = JIRA_CODE_PROMPT.format(
            task_id=context.task_id,
            issue_key=issue.get("key", "unknown"),
            project=fields.get("project", {}).get("key", "unknown"),
            summary=fields.get("summary", "No summary"),
            description=fields.get("description", "No description"),
            issue_type=fields.get("issuetype", {}).get("name", "unknown"),
            priority=fields.get("priority", {}).get("name", "Medium"),
            labels=", ".join(fields.get("labels", [])),
        )

        result = await self._execute_cli(prompt, working_dir)

        return AgentResult(
            success=result.get("success", False),
            output=result.get("output", ""),
            agent_type=self.agent_type,
            next_agent=AgentType.PLANNING,
            artifacts={
                "issue_key": issue.get("key"),
                "project": fields.get("project", {}).get("key"),
            },
            should_respond=True,
            response_channel=f"jira:{issue.get('key')}",
        )

    def _get_working_dir(self, context: AgentContext, fields: dict) -> str:
        repo_field = fields.get("customfield_repository", "")
        if repo_field:
            repo_name = repo_field.split("/")[-1]
            return f"/app/repos/{repo_name}"
        if context.repository:
            repo_name = context.repository.split("/")[-1]
            return f"/app/repos/{repo_name}"
        return "/app/repos/default"
