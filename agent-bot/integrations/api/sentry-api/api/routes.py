"""Sentry API routes."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
import structlog
import sys

sys.path.insert(0, "../../packages")
from sentry_client import SentryClient, SentryAPIError

router = APIRouter()
logger = structlog.get_logger()


@router.get("/issues/{issue_id}")
async def get_issue(issue_id: str, auth_token: str) -> dict[str, Any]:
    """Get issue by ID."""
    try:
        async with SentryClient(auth_token=auth_token) as client:
            issue = await client.get_issue(issue_id)
            return issue.model_dump()
    except SentryAPIError as e:
        logger.error("sentry_api_error", error=str(e), issue_id=issue_id)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.get("/organizations/{organization}/issues")
async def search_issues(
    organization: str, project: str, auth_token: str, query: str | None = None
) -> list[dict[str, Any]]:
    """Search issues in a project."""
    try:
        async with SentryClient(auth_token=auth_token) as client:
            issues = await client.search_issues(organization, project, query)
            return [issue.model_dump() for issue in issues]
    except SentryAPIError as e:
        logger.error("sentry_api_error", error=str(e), organization=organization)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.put("/issues/{issue_id}")
async def update_issue(
    issue_id: str,
    auth_token: str,
    status_update: str | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    """Update issue status or assignee."""
    try:
        async with SentryClient(auth_token=auth_token) as client:
            issue = await client.update_issue(issue_id, status_update, assigned_to)
            return issue.model_dump()
    except SentryAPIError as e:
        logger.error("sentry_api_error", error=str(e), issue_id=issue_id)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )
