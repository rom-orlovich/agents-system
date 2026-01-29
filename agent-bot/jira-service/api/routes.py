from fastapi import APIRouter, HTTPException, status
from api.models import (
    AddCommentRequest,
    AddCommentResponse,
    GetIssueRequest,
    GetIssueResponse,
    UpdateIssueStatusRequest,
    UpdateIssueStatusResponse,
    CreateIssueRequest,
    CreateIssueResponse,
)
from client.jira_client import JiraClient
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/jira", tags=["jira"])

jira_client = JiraClient()


@router.post("/issue/{issue_key}/comment", response_model=AddCommentResponse)
async def add_comment_to_issue(issue_key: str, request: AddCommentRequest):
    try:
        result = await jira_client.add_comment(issue_key, request.comment)
        return AddCommentResponse(
            success=True,
            comment_id=result.get("id"),
            message="Comment added successfully",
            error=None,
        )
    except Exception as e:
        logger.error("add_comment_failed", issue_key=issue_key, error=str(e))
        return AddCommentResponse(
            success=False,
            comment_id=None,
            message="Failed to add comment",
            error=str(e),
        )


@router.get("/issue/{issue_key}", response_model=GetIssueResponse)
async def get_issue_details(issue_key: str):
    try:
        issue = await jira_client.get_issue(issue_key)
        fields = issue.get("fields", {})
        assignee = fields.get("assignee", {})
        reporter = fields.get("reporter", {})
        status_obj = fields.get("status", {})

        return GetIssueResponse(
            success=True,
            issue_key=issue.get("key"),
            summary=fields.get("summary"),
            description=str(fields.get("description", "")),
            status=status_obj.get("name") if status_obj else None,
            assignee=assignee.get("displayName") if assignee else None,
            reporter=reporter.get("displayName") if reporter else None,
            error=None,
        )
    except Exception as e:
        logger.error("get_issue_failed", issue_key=issue_key, error=str(e))
        return GetIssueResponse(
            success=False,
            issue_key=None,
            summary=None,
            description=None,
            status=None,
            assignee=None,
            reporter=None,
            error=str(e),
        )


@router.post("/issue/{issue_key}/transition", response_model=UpdateIssueStatusResponse)
async def transition_issue(issue_key: str, request: UpdateIssueStatusRequest):
    try:
        await jira_client.transition_issue(issue_key, request.transition_id)
        return UpdateIssueStatusResponse(
            success=True, message="Issue transitioned successfully", error=None
        )
    except Exception as e:
        logger.error("transition_issue_failed", issue_key=issue_key, error=str(e))
        return UpdateIssueStatusResponse(
            success=False, message="Failed to transition issue", error=str(e)
        )


@router.post("/issue", response_model=CreateIssueResponse)
async def create_issue(request: CreateIssueRequest):
    try:
        result = await jira_client.create_issue(
            request.project_key,
            request.summary,
            request.description,
            request.issue_type,
        )
        return CreateIssueResponse(
            success=True,
            issue_key=result.get("key"),
            issue_id=result.get("id"),
            message="Issue created successfully",
            error=None,
        )
    except Exception as e:
        logger.error("create_issue_failed", error=str(e))
        return CreateIssueResponse(
            success=False,
            issue_key=None,
            issue_id=None,
            message="Failed to create issue",
            error=str(e),
        )
