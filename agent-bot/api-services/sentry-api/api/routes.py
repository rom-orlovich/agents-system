from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from client import SentryClient
from config import get_settings, Settings

router = APIRouter(prefix="/api/v1", tags=["sentry"])


def get_sentry_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SentryClient:
    return SentryClient(
        auth_token=settings.sentry_auth_token,
        org_slug=settings.sentry_org_slug,
        base_url=settings.sentry_api_base_url,
        timeout=settings.request_timeout,
    )


class UpdateIssueStatusRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    status: Literal["resolved", "unresolved", "ignored"]


class AddCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    text: str


class AssignIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    assignee_id: str | None = None


@router.get("/projects")
async def list_projects(
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.list_projects()


@router.get("/projects/{project_slug}/issues")
async def get_project_issues(
    project_slug: str,
    query: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    client: Annotated[SentryClient, Depends(get_sentry_client)] = None,
):
    return await client.get_project_issues(project_slug, query, cursor)


@router.get("/issues/{issue_id}")
async def get_issue(
    issue_id: str,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.get_issue(issue_id)


@router.get("/issues/{issue_id}/events")
async def get_issue_events(
    issue_id: str,
    cursor: Annotated[str | None, Query()] = None,
    client: Annotated[SentryClient, Depends(get_sentry_client)] = None,
):
    return await client.get_issue_events(issue_id, cursor)


@router.get("/issues/{issue_id}/events/latest")
async def get_latest_event(
    issue_id: str,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.get_latest_event(issue_id)


@router.put("/issues/{issue_id}/status")
async def update_issue_status(
    issue_id: str,
    request: UpdateIssueStatusRequest,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.update_issue_status(issue_id, request.status)


@router.post("/issues/{issue_id}/comments")
async def add_comment(
    issue_id: str,
    request: AddCommentRequest,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.add_comment(issue_id, request.text)


@router.get("/issues/{issue_id}/hashes")
async def get_issue_hashes(
    issue_id: str,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.get_issue_hashes(issue_id)


@router.get("/issues/{issue_id}/tags")
async def get_issue_tags(
    issue_id: str,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.get_issue_tags(issue_id)


@router.put("/issues/{issue_id}/assign")
async def assign_issue(
    issue_id: str,
    request: AssignIssueRequest,
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.assign_issue(issue_id, request.assignee_id)


@router.get("/members")
async def get_organization_members(
    client: Annotated[SentryClient, Depends(get_sentry_client)],
):
    return await client.get_organization_members()
