import os
import asyncio
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from fastapi import FastAPI, HTTPException
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import structlog
from base64 import b64encode
import uvicorn

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

mcp_server = Server("jira-mcp-server")
rest_api = FastAPI(title="Jira MCP Server", description="Dual-purpose: MCP + REST API")


class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
    comment: str = Field(..., description="Comment body", min_length=1)


class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: str | None = Field(None)
    message: str


class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key")


class JiraIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    title: str | None = Field(None)
    status: str | None = Field(None)
    description: str | None = Field(None)


class CreateIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_key: str = Field(..., description="Project key")
    summary: str = Field(..., description="Issue summary", min_length=1)
    description: str = Field(..., description="Issue description")
    issue_type: str = Field(..., description="Issue type (Bug, Task, Story, etc.)")


class CreateIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    message: str


def get_auth_header() -> str:
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not jira_email or not jira_api_token:
        raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN must be configured")

    credentials = f"{jira_email}:{jira_api_token}"
    encoded = b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def get_base_url() -> str:
    jira_domain = os.getenv("JIRA_DOMAIN")
    if not jira_domain:
        raise ValueError("JIRA_DOMAIN not configured")
    return f"https://{jira_domain}/rest/api/3"


async def jira_add_comment_impl(issue_key: str, comment: str) -> AddCommentResponse:
    try:
        auth_header = get_auth_header()
        base_url = get_base_url()
    except ValueError as e:
        return AddCommentResponse(success=False, comment_id=None, message=str(e))

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{base_url}/issue/{issue_key}/comment"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                headers=headers,
                json={"body": comment},
                timeout=30.0,
            )
            response.raise_for_status()

            result = response.json()
            logger.info("jira_comment_added", issue_key=issue_key, comment_id=result.get("id"))

            return AddCommentResponse(
                success=True,
                comment_id=str(result.get("id")),
                message=f"Successfully added comment to {issue_key}",
            )
        except httpx.HTTPError as e:
            logger.error("jira_comment_failed", issue_key=issue_key, error=str(e))
            return AddCommentResponse(
                success=False, comment_id=None, message=f"Error adding comment: {str(e)}"
            )


async def jira_get_issue_impl(issue_key: str) -> JiraIssueResponse:
    try:
        auth_header = get_auth_header()
        base_url = get_base_url()
    except ValueError as e:
        return JiraIssueResponse(
            success=False, issue_key=None, title=None, status=None, description=None
        )

    headers = {"Authorization": auth_header, "Accept": "application/json"}
    url = f"{base_url}/issue/{issue_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()

            result = response.json()
            fields = result.get("fields", {})

            return JiraIssueResponse(
                success=True,
                issue_key=issue_key,
                title=fields.get("summary"),
                status=fields.get("status", {}).get("name"),
                description=fields.get("description"),
            )
        except httpx.HTTPError as e:
            logger.error("jira_get_issue_failed", issue_key=issue_key, error=str(e))
            return JiraIssueResponse(
                success=False, issue_key=None, title=None, status=None, description=None
            )


async def jira_create_issue_impl(
    project_key: str, summary: str, description: str, issue_type: str
) -> CreateIssueResponse:
    try:
        auth_header = get_auth_header()
        base_url = get_base_url()
    except ValueError as e:
        return CreateIssueResponse(success=False, issue_key=None, message=str(e))

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{base_url}/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()
            issue_key = result.get("key")
            logger.info("jira_issue_created", issue_key=issue_key, project=project_key)

            return CreateIssueResponse(
                success=True,
                issue_key=issue_key,
                message=f"Successfully created issue {issue_key}",
            )
        except httpx.HTTPError as e:
            logger.error("jira_create_issue_failed", project=project_key, error=str(e))
            return CreateIssueResponse(
                success=False, issue_key=None, message=f"Error creating issue: {str(e)}"
            )


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="jira_add_comment",
            description="Add a comment to a Jira issue",
            inputSchema=AddCommentInput.model_json_schema(),
        ),
        Tool(
            name="jira_get_issue",
            description="Get details of a Jira issue",
            inputSchema=GetIssueInput.model_json_schema(),
        ),
        Tool(
            name="jira_create_issue",
            description="Create a new Jira issue",
            inputSchema=CreateIssueInput.model_json_schema(),
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "jira_add_comment":
        validated_input = AddCommentInput.model_validate(arguments)
        result = await jira_add_comment_impl(
            validated_input.issue_key, validated_input.comment
        )
        return [TextContent(type="text", text=result.message)]

    elif name == "jira_get_issue":
        validated_input = GetIssueInput.model_validate(arguments)
        result = await jira_get_issue_impl(validated_input.issue_key)

        if result.success:
            text = f"Issue {result.issue_key}:\nTitle: {result.title}\nStatus: {result.status}\nDescription: {result.description}"
        else:
            text = "Failed to get issue"

        return [TextContent(type="text", text=text)]

    elif name == "jira_create_issue":
        validated_input = CreateIssueInput.model_validate(arguments)
        result = await jira_create_issue_impl(
            validated_input.project_key,
            validated_input.summary,
            validated_input.description,
            validated_input.issue_type,
        )
        return [TextContent(type="text", text=result.message)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


@rest_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "jira-mcp-server", "mode": "dual"}


@rest_api.post("/api/v1/jira/issue/{issue_key}/comment", response_model=AddCommentResponse)
async def add_comment_rest(issue_key: str, request: AddCommentInput):
    return await jira_add_comment_impl(issue_key, request.comment)


@rest_api.get("/api/v1/jira/issue/{issue_key}", response_model=JiraIssueResponse)
async def get_issue_rest(issue_key: str):
    return await jira_get_issue_impl(issue_key)


@rest_api.post("/api/v1/jira/issue", response_model=CreateIssueResponse)
async def create_issue_rest(request: CreateIssueInput):
    return await jira_create_issue_impl(
        request.project_key, request.summary, request.description, request.issue_type
    )


async def run_mcp_server():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
        )


async def run_rest_server():
    config = uvicorn.Config(rest_api, host="0.0.0.0", port=8082, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    mode = os.getenv("SERVER_MODE", "both")

    if mode == "mcp":
        await run_mcp_server()
    elif mode == "rest":
        await run_rest_server()
    else:
        await asyncio.gather(run_mcp_server(), run_rest_server())


if __name__ == "__main__":
    asyncio.run(main())
