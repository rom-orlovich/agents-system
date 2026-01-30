import os
from mcp.server import Server
from mcp.types import Tool, TextContent
import structlog

from sentry_client import (
    SentryClient,
    AddCommentInput,
    UpdateIssueStatusInput,
    GetIssueInput,
    AssignIssueInput,
    AddTagInput,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

mcp_server = Server("sentry-mcp-server")


def get_sentry_client() -> SentryClient:
    auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    org_slug = os.getenv("SENTRY_ORG_SLUG")
    project_slug = os.getenv("SENTRY_PROJECT_SLUG")

    if not auth_token or not org_slug or not project_slug:
        raise ValueError(
            "SENTRY_AUTH_TOKEN, SENTRY_ORG_SLUG, and SENTRY_PROJECT_SLUG must be configured"
        )

    return SentryClient(
        auth_token=auth_token, org_slug=org_slug, project_slug=project_slug
    )


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="sentry_add_comment",
            description="Add a comment to a Sentry issue",
            inputSchema=AddCommentInput.model_json_schema(),
        ),
        Tool(
            name="sentry_update_status",
            description="Update the status of a Sentry issue",
            inputSchema=UpdateIssueStatusInput.model_json_schema(),
        ),
        Tool(
            name="sentry_get_issue",
            description="Get details of a Sentry issue",
            inputSchema=GetIssueInput.model_json_schema(),
        ),
        Tool(
            name="sentry_assign_issue",
            description="Assign a Sentry issue to a user or team",
            inputSchema=AssignIssueInput.model_json_schema(),
        ),
        Tool(
            name="sentry_add_tag",
            description="Add a tag to a Sentry issue",
            inputSchema=AddTagInput.model_json_schema(),
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    client = get_sentry_client()

    if name == "sentry_add_comment":
        validated_input = AddCommentInput.model_validate(arguments)
        result = await client.add_comment(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "sentry_update_status":
        validated_input = UpdateIssueStatusInput.model_validate(arguments)
        result = await client.update_issue_status(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "sentry_get_issue":
        validated_input = GetIssueInput.model_validate(arguments)
        result = await client.get_issue(validated_input)

        if result.success:
            text = f"Issue {result.issue_id}:\nTitle: {result.title}\nStatus: {result.status}\nLevel: {result.level}\nCulprit: {result.culprit}"
        else:
            text = "Failed to get issue"

        return [TextContent(type="text", text=text)]

    elif name == "sentry_assign_issue":
        validated_input = AssignIssueInput.model_validate(arguments)
        result = await client.assign_issue(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "sentry_add_tag":
        validated_input = AddTagInput.model_validate(arguments)
        result = await client.add_tag(validated_input)
        return [TextContent(type="text", text=result.message)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
