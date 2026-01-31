from typing import Any
from fastmcp import FastMCP

from sentry_mcp import SentryAPI
from config import get_settings

mcp = FastMCP("Sentry MCP Server")
sentry_api = SentryAPI()


@mcp.tool()
async def list_sentry_projects() -> list[dict[str, Any]]:
    """
    List all Sentry projects in the organization.

    Returns:
        List of projects with their slugs and details
    """
    return await sentry_api.list_projects()


@mcp.tool()
async def get_sentry_project_issues(
    project_slug: str,
    query: str | None = None,
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get issues for a Sentry project.

    Args:
        project_slug: The project slug (e.g., my-project)
        query: Optional query to filter issues
        cursor: Pagination cursor

    Returns:
        List of issues in the project
    """
    return await sentry_api.get_project_issues(project_slug, query, cursor)


@mcp.tool()
async def get_sentry_issue(issue_id: str) -> dict[str, Any]:
    """
    Get details of a specific Sentry issue.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        Issue details including title, culprit, and statistics
    """
    return await sentry_api.get_issue(issue_id)


@mcp.tool()
async def get_sentry_issue_events(
    issue_id: str, cursor: str | None = None
) -> list[dict[str, Any]]:
    """
    Get events for a Sentry issue.

    Args:
        issue_id: The Sentry issue ID
        cursor: Pagination cursor

    Returns:
        List of events for the issue
    """
    return await sentry_api.get_issue_events(issue_id, cursor)


@mcp.tool()
async def get_sentry_latest_event(issue_id: str) -> dict[str, Any]:
    """
    Get the latest event for a Sentry issue.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        Latest event details including stacktrace and context
    """
    return await sentry_api.get_latest_event(issue_id)


@mcp.tool()
async def resolve_sentry_issue(issue_id: str) -> dict[str, Any]:
    """
    Mark a Sentry issue as resolved.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        Updated issue details
    """
    return await sentry_api.update_issue_status(issue_id, "resolved")


@mcp.tool()
async def ignore_sentry_issue(issue_id: str) -> dict[str, Any]:
    """
    Mark a Sentry issue as ignored.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        Updated issue details
    """
    return await sentry_api.update_issue_status(issue_id, "ignored")


@mcp.tool()
async def unresolve_sentry_issue(issue_id: str) -> dict[str, Any]:
    """
    Mark a Sentry issue as unresolved.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        Updated issue details
    """
    return await sentry_api.update_issue_status(issue_id, "unresolved")


@mcp.tool()
async def add_sentry_comment(issue_id: str, text: str) -> dict[str, Any]:
    """
    Add a comment to a Sentry issue.

    Args:
        issue_id: The Sentry issue ID
        text: Comment text

    Returns:
        Created comment details
    """
    return await sentry_api.add_comment(issue_id, text)


@mcp.tool()
async def get_sentry_issue_tags(issue_id: str) -> list[dict[str, Any]]:
    """
    Get tags for a Sentry issue.

    Args:
        issue_id: The Sentry issue ID

    Returns:
        List of tags with their values
    """
    return await sentry_api.get_issue_tags(issue_id)


if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", port=settings.port)
