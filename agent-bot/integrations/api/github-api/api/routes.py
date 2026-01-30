"""GitHub API routes."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
import structlog
import sys

sys.path.insert(0, "../../packages")
from github_client import GitHubClient, GitHubAPIError

router = APIRouter()
logger = structlog.get_logger()


@router.get("/repos/{owner}/{repo}")
async def get_repository(owner: str, repo: str, token: str) -> dict[str, Any]:
    """Get repository details."""
    try:
        async with GitHubClient(token=token) as client:
            repository = await client.get_repository(owner, repo)
            return repository.model_dump()
    except GitHubAPIError as e:
        logger.error("github_api_error", error=str(e), owner=owner, repo=repo)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.get("/repos/{owner}/{repo}/pulls")
async def list_pull_requests(
    owner: str, repo: str, token: str, state: str = "open"
) -> list[dict[str, Any]]:
    """List pull requests."""
    try:
        async with GitHubClient(token=token) as client:
            prs = await client.list_pull_requests(owner, repo, state)
            return [pr.model_dump() for pr in prs]
    except GitHubAPIError as e:
        logger.error("github_api_error", error=str(e), owner=owner, repo=repo)
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/comments")
async def create_comment(
    owner: str, repo: str, issue_number: int, body: str, token: str
) -> dict[str, Any]:
    """Create issue comment."""
    try:
        async with GitHubClient(token=token) as client:
            comment = await client.create_issue_comment(owner, repo, issue_number, body)
            return comment.model_dump()
    except GitHubAPIError as e:
        logger.error(
            "github_api_error", error=str(e), owner=owner, repo=repo, issue=issue_number
        )
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )
