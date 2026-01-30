"""Jira API routes."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
import structlog
import sys

sys.path.insert(0, "../../packages")
from jira_client import JiraClient, JiraAPIError

router = APIRouter()
logger = structlog.get_logger()


@router.get("/issues/{issue_key}")
async def get_issue(issue_key: str, jira_url: str, jira_email: str, jira_api_key: str) -> dict[str, Any]:
    """Get issue by key."""
    try:
        async with JiraClient(url=jira_url, email=jira_email, api_token=jira_api_key) as client:
            issue = await client.get_issue(issue_key)
            return issue.model_dump()
    except JiraAPIError as e:
        logger.error("jira_api_error", error=str(e), issue_key=issue_key)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.get("/search")
async def search_issues(
    jql: str, jira_url: str, jira_email: str, jira_api_key: str, max_results: int = 50
) -> list[dict[str, Any]]:
    """Search issues using JQL."""
    try:
        async with JiraClient(url=jira_url, email=jira_email, api_token=jira_api_key) as client:
            issues = await client.search_issues(jql, max_results)
            return [issue.model_dump() for issue in issues]
    except JiraAPIError as e:
        logger.error("jira_api_error", error=str(e), jql=jql)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.post("/issues/{issue_key}/transitions")
async def transition_issue(
    issue_key: str, transition_id: str, jira_url: str, jira_email: str, jira_api_key: str
) -> dict[str, str]:
    """Transition issue to new status."""
    try:
        async with JiraClient(url=jira_url, email=jira_email, api_token=jira_api_key) as client:
            await client.transition_issue(issue_key, transition_id)
            return {"status": "success", "issue_key": issue_key, "transition_id": transition_id}
    except JiraAPIError as e:
        logger.error("jira_api_error", error=str(e), issue_key=issue_key)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )
