from fastapi import APIRouter, Depends, HTTPException, status
from api.models import (
    PostPRCommentRequest,
    PostPRCommentResponse,
    PostIssueCommentRequest,
    PostIssueCommentResponse,
    GetPRDetailsResponse,
    GetIssueDetailsResponse,
)
from client.github_client import GitHubClient
import structlog
import os

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub Service"],
    responses={404: {"description": "Not found"}},
)


def get_github_client() -> GitHubClient:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub token not configured",
        )
    return GitHubClient(token=token)


@router.post(
    "/pr/{owner}/{repo}/{pr_number}/comment",
    response_model=PostPRCommentResponse,
    summary="Post comment to GitHub PR",
    description="Post a comment to a GitHub pull request.",
)
async def post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    request: PostPRCommentRequest,
    client: GitHubClient = Depends(get_github_client),
) -> PostPRCommentResponse:
    result = await client.post_pr_comment(
        owner=owner, repo=repo, pr_number=pr_number, comment=request.comment
    )

    return PostPRCommentResponse(
        success=result.get("success", False),
        comment_id=result.get("comment_id"),
        message=result.get("message", ""),
        error=result.get("error"),
    )


@router.post(
    "/issue/{owner}/{repo}/{issue_number}/comment",
    response_model=PostIssueCommentResponse,
    summary="Post comment to GitHub issue",
    description="Post a comment to a GitHub issue.",
)
async def post_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    request: PostIssueCommentRequest,
    client: GitHubClient = Depends(get_github_client),
) -> PostIssueCommentResponse:
    result = await client.post_issue_comment(
        owner=owner, repo=repo, issue_number=issue_number, comment=request.comment
    )

    return PostIssueCommentResponse(
        success=result.get("success", False),
        comment_id=result.get("comment_id"),
        message=result.get("message", ""),
        error=result.get("error"),
    )


@router.get(
    "/pr/{owner}/{repo}/{pr_number}",
    response_model=GetPRDetailsResponse,
    summary="Get GitHub PR details",
    description="Get details of a GitHub pull request.",
)
async def get_pr_details(
    owner: str,
    repo: str,
    pr_number: int,
    client: GitHubClient = Depends(get_github_client),
) -> GetPRDetailsResponse:
    result = await client.get_pr_details(owner=owner, repo=repo, pr_number=pr_number)

    return GetPRDetailsResponse(
        success=result.get("success", False),
        pr_number=result.get("pr_number"),
        title=result.get("title"),
        body=result.get("body"),
        state=result.get("state"),
        merged=result.get("merged"),
        error=result.get("error"),
    )


@router.get(
    "/issue/{owner}/{repo}/{issue_number}",
    response_model=GetIssueDetailsResponse,
    summary="Get GitHub issue details",
    description="Get details of a GitHub issue.",
)
async def get_issue_details(
    owner: str,
    repo: str,
    issue_number: int,
    client: GitHubClient = Depends(get_github_client),
) -> GetIssueDetailsResponse:
    result = await client.get_issue_details(
        owner=owner, repo=repo, issue_number=issue_number
    )

    return GetIssueDetailsResponse(
        success=result.get("success", False),
        issue_number=result.get("issue_number"),
        title=result.get("title"),
        body=result.get("body"),
        state=result.get("state"),
        error=result.get("error"),
    )
