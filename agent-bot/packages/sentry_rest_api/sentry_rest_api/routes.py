import os
from fastapi import FastAPI, HTTPException
import structlog

from sentry_client import (
    SentryClient,
    AddCommentInput,
    AddCommentResponse,
    UpdateIssueStatusInput,
    UpdateIssueStatusResponse,
    GetIssueInput,
    SentryIssueResponse,
    AssignIssueInput,
    AssignIssueResponse,
    AddTagInput,
    AddTagResponse,
    SentryAuthenticationError,
    SentryNotFoundError,
    SentryValidationError,
    SentryRateLimitError,
    SentryServerError,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

app = FastAPI(
    title="Sentry REST API",
    description="REST API for Sentry using shared client",
    version="0.1.0",
)


def get_sentry_client() -> SentryClient:
    auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    org_slug = os.getenv("SENTRY_ORG_SLUG")
    project_slug = os.getenv("SENTRY_PROJECT_SLUG")

    if not auth_token or not org_slug or not project_slug:
        raise HTTPException(
            status_code=500,
            detail="SENTRY_AUTH_TOKEN, SENTRY_ORG_SLUG, and SENTRY_PROJECT_SLUG must be configured",
        )

    return SentryClient(
        auth_token=auth_token, org_slug=org_slug, project_slug=project_slug
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sentry-rest-api"}


@app.post("/api/v1/sentry/issue/{issue_id}/comment", response_model=AddCommentResponse)
async def add_comment(issue_id: str, request: AddCommentInput):
    try:
        client = get_sentry_client()
        return await client.add_comment(request)
    except SentryAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SentryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SentryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SentryRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except SentryServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.put("/api/v1/sentry/issue/{issue_id}/status", response_model=UpdateIssueStatusResponse)
async def update_issue_status(issue_id: str, request: UpdateIssueStatusInput):
    try:
        client = get_sentry_client()
        return await client.update_issue_status(request)
    except SentryAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SentryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SentryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SentryServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/sentry/issue/{issue_id}", response_model=SentryIssueResponse)
async def get_issue(issue_id: str):
    try:
        client = get_sentry_client()
        input_data = GetIssueInput(issue_id=issue_id)
        return await client.get_issue(input_data)
    except SentryAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SentryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SentryServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.put("/api/v1/sentry/issue/{issue_id}/assign", response_model=AssignIssueResponse)
async def assign_issue(issue_id: str, request: AssignIssueInput):
    try:
        client = get_sentry_client()
        return await client.assign_issue(request)
    except SentryAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SentryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SentryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SentryServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/v1/sentry/issue/{issue_id}/tag", response_model=AddTagResponse)
async def add_tag(issue_id: str, request: AddTagInput):
    try:
        client = get_sentry_client()
        return await client.add_tag(request)
    except SentryAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SentryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SentryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SentryServerError as e:
        raise HTTPException(status_code=502, detail=str(e))
