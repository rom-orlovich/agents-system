from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from client import GitHubClient
from config import get_settings, Settings

router = APIRouter(prefix="/api/v1", tags=["github"])


def get_github_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GitHubClient:
    return GitHubClient(
        token=settings.github_token,
        base_url=settings.github_api_base_url,
        timeout=settings.request_timeout,
    )


class CreateIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    title: str
    body: str | None = None
    labels: list[str] | None = None


class CreateCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    body: str


class CreatePRReviewCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    body: str
    commit_id: str
    path: str
    line: int


@router.get("/repos/{owner}/{repo}")
async def get_repository(
    owner: str,
    repo: str,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.get_repository(owner, repo)


@router.get("/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(
    owner: str,
    repo: str,
    issue_number: int,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.get_issue(owner, repo, issue_number)


@router.post("/repos/{owner}/{repo}/issues")
async def create_issue(
    owner: str,
    repo: str,
    request: CreateIssueRequest,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.create_issue(
        owner, repo, request.title, request.body, request.labels
    )


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/comments")
async def create_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    request: CreateCommentRequest,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.create_issue_comment(owner, repo, issue_number, request.body)


@router.get("/repos/{owner}/{repo}/pulls/{pr_number}")
async def get_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.get_pull_request(owner, repo, pr_number)


@router.post("/repos/{owner}/{repo}/pulls/{pr_number}/comments")
async def create_pr_review_comment(
    owner: str,
    repo: str,
    pr_number: int,
    request: CreatePRReviewCommentRequest,
    client: Annotated[GitHubClient, Depends(get_github_client)],
):
    return await client.create_pr_review_comment(
        owner,
        repo,
        pr_number,
        request.body,
        request.commit_id,
        request.path,
        request.line,
    )


@router.get("/repos/{owner}/{repo}/contents/{path:path}")
async def get_file_contents(
    owner: str,
    repo: str,
    path: str,
    ref: Annotated[str | None, Query()] = None,
    client: Annotated[GitHubClient, Depends(get_github_client)] = None,
):
    return await client.get_file_contents(owner, repo, path, ref)


@router.get("/search/code")
async def search_code(
    q: Annotated[str, Query()],
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
    page: Annotated[int, Query(ge=1)] = 1,
    client: Annotated[GitHubClient, Depends(get_github_client)] = None,
):
    return await client.search_code(q, per_page, page)


@router.get("/repos/{owner}/{repo}/branches")
async def list_branches(
    owner: str,
    repo: str,
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
    page: Annotated[int, Query(ge=1)] = 1,
    client: Annotated[GitHubClient, Depends(get_github_client)] = None,
):
    return await client.list_branches(owner, repo, per_page, page)
