from typing import Annotated, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from client import JiraClient
from config import get_settings, Settings

router = APIRouter(prefix="/api/v1", tags=["jira"])


def get_jira_client(settings: Annotated[Settings, Depends(get_settings)]) -> JiraClient:
    return JiraClient(
        base_url=settings.jira_url,
        email=settings.jira_email,
        api_token=settings.jira_api_token,
        timeout=settings.request_timeout,
    )


class CreateIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    project_key: str
    summary: str
    description: str
    issue_type: str = "Task"


class UpdateIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    fields: dict[str, Any]


class AddCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    body: str


class SearchIssuesRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    jql: str
    max_results: int = 50
    start_at: int = 0


class TransitionIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    transition_id: str


@router.get("/issues/{issue_key}")
async def get_issue(
    issue_key: str,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.get_issue(issue_key)


@router.post("/issues")
async def create_issue(
    request: CreateIssueRequest,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.create_issue(
        request.project_key,
        request.summary,
        request.description,
        request.issue_type,
    )


@router.put("/issues/{issue_key}")
async def update_issue(
    issue_key: str,
    request: UpdateIssueRequest,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.update_issue(issue_key, request.fields)


@router.post("/issues/{issue_key}/comments")
async def add_comment(
    issue_key: str,
    request: AddCommentRequest,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.add_comment(issue_key, request.body)


@router.post("/search")
async def search_issues(
    request: SearchIssuesRequest,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.search_issues(
        request.jql, request.max_results, request.start_at
    )


@router.get("/issues/{issue_key}/transitions")
async def get_transitions(
    issue_key: str,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.get_transitions(issue_key)


@router.post("/issues/{issue_key}/transitions")
async def transition_issue(
    issue_key: str,
    request: TransitionIssueRequest,
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.transition_issue(issue_key, request.transition_id)


@router.get("/projects")
async def get_projects(
    client: Annotated[JiraClient, Depends(get_jira_client)],
):
    return await client.get_projects()
