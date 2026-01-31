from typing import Any
from fastmcp import FastMCP

from jira_mcp import JiraAPI
from config import get_settings

mcp = FastMCP("Jira MCP Server")
jira_api = JiraAPI()


@mcp.tool()
async def get_jira_issue(issue_key: str) -> dict[str, Any]:
    """
    Get details of a Jira issue.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)

    Returns:
        Issue details including summary, description, status, and assignee
    """
    return await jira_api.get_issue(issue_key)


@mcp.tool()
async def create_jira_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
) -> dict[str, Any]:
    """
    Create a new Jira issue.

    Args:
        project_key: The project key (e.g., PROJ)
        summary: Issue title/summary
        description: Detailed description of the issue
        issue_type: Type of issue (Task, Bug, Story, etc.)

    Returns:
        Created issue details including the new issue key
    """
    return await jira_api.create_issue(project_key, summary, description, issue_type)


@mcp.tool()
async def update_jira_issue(issue_key: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Update fields of an existing Jira issue.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)
        fields: Dictionary of fields to update

    Returns:
        Success status
    """
    return await jira_api.update_issue(issue_key, fields)


@mcp.tool()
async def add_jira_comment(issue_key: str, body: str) -> dict[str, Any]:
    """
    Add a comment to a Jira issue.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)
        body: Comment text

    Returns:
        Created comment details
    """
    return await jira_api.add_comment(issue_key, body)


@mcp.tool()
async def search_jira_issues(
    jql: str, max_results: int = 50, start_at: int = 0
) -> dict[str, Any]:
    """
    Search for Jira issues using JQL.

    Args:
        jql: JQL query string
        max_results: Maximum number of results to return
        start_at: Index to start from for pagination

    Returns:
        Search results with matching issues
    """
    return await jira_api.search_issues(jql, max_results, start_at)


@mcp.tool()
async def get_jira_transitions(issue_key: str) -> dict[str, Any]:
    """
    Get available transitions for a Jira issue.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)

    Returns:
        List of available transitions
    """
    return await jira_api.get_transitions(issue_key)


@mcp.tool()
async def transition_jira_issue(issue_key: str, transition_id: str) -> dict[str, Any]:
    """
    Transition a Jira issue to a new status.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)
        transition_id: ID of the transition to perform

    Returns:
        Success status
    """
    return await jira_api.transition_issue(issue_key, transition_id)


if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", port=settings.port)
