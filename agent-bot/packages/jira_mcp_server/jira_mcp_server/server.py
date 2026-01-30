import os
from mcp.server import Server
from mcp.types import Tool, TextContent
import structlog

from jira_client import (
    JiraClient,
    AddCommentInput,
    GetIssueInput,
    CreateIssueInput,
    TransitionIssueInput,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

mcp_server = Server("jira-mcp-server")


def get_jira_client() -> JiraClient:
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    domain = os.getenv("JIRA_DOMAIN")

    if not email or not api_token or not domain:
        raise ValueError(
            "JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_DOMAIN must be configured"
        )

    return JiraClient(email=email, api_token=api_token, domain=domain)


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
        Tool(
            name="jira_transition_issue",
            description="Transition a Jira issue to a new status",
            inputSchema=TransitionIssueInput.model_json_schema(),
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    client = get_jira_client()

    if name == "jira_add_comment":
        validated_input = AddCommentInput.model_validate(arguments)
        result = await client.add_comment(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "jira_get_issue":
        validated_input = GetIssueInput.model_validate(arguments)
        result = await client.get_issue(validated_input)

        if result.success:
            text = f"Issue {result.issue_key}:\nTitle: {result.title}\nStatus: {result.status}\nDescription: {result.description}"
        else:
            text = "Failed to get issue"

        return [TextContent(type="text", text=text)]

    elif name == "jira_create_issue":
        validated_input = CreateIssueInput.model_validate(arguments)
        result = await client.create_issue(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "jira_transition_issue":
        validated_input = TransitionIssueInput.model_validate(arguments)
        result = await client.transition_issue(validated_input)
        return [TextContent(type="text", text=result.message)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
