import os
from fastapi import FastAPI, HTTPException
import structlog

from jira_client import (
    JiraClient,
    AddCommentInput,
    AddCommentResponse,
    GetIssueInput,
    JiraIssueResponse,
    CreateIssueInput,
    CreateIssueResponse,
    TransitionIssueInput,
    TransitionIssueResponse,
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraValidationError,
    JiraRateLimitError,
    JiraServerError,
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
    title="Jira REST API",
    description="REST API for Jira using shared client",
    version="0.1.0",
)


def get_jira_client() -> JiraClient:
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    domain = os.getenv("JIRA_DOMAIN")

    if not email or not api_token or not domain:
        raise HTTPException(
            status_code=500,
            detail="JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_DOMAIN must be configured",
        )

    return JiraClient(email=email, api_token=api_token, domain=domain)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "jira-rest-api"}


@app.post("/api/v1/jira/issue/{issue_key}/comment", response_model=AddCommentResponse)
async def add_comment(issue_key: str, request: AddCommentInput):
    try:
        client = get_jira_client()
        return await client.add_comment(request)
    except JiraAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except JiraNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except JiraValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except JiraRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except JiraServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/jira/issue/{issue_key}", response_model=JiraIssueResponse)
async def get_issue(issue_key: str):
    try:
        client = get_jira_client()
        input_data = GetIssueInput(issue_key=issue_key)
        return await client.get_issue(input_data)
    except JiraAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except JiraNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except JiraServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/v1/jira/issue", response_model=CreateIssueResponse)
async def create_issue(request: CreateIssueInput):
    try:
        client = get_jira_client()
        return await client.create_issue(request)
    except JiraAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except JiraValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except JiraRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except JiraServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post(
    "/api/v1/jira/issue/{issue_key}/transitions",
    response_model=TransitionIssueResponse,
)
async def transition_issue(issue_key: str, request: TransitionIssueInput):
    try:
        client = get_jira_client()
        return await client.transition_issue(request)
    except JiraAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except JiraNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except JiraValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except JiraServerError as e:
        raise HTTPException(status_code=502, detail=str(e))
