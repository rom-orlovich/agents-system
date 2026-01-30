import os
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import structlog
from base64 import b64encode

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

server = Server("jira-mcp-server")


class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
    comment: str = Field(..., description="Comment body", min_length=1)


class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key")


class CreateIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_key: str = Field(..., description="Project key")
    summary: str = Field(..., description="Issue summary", min_length=1)
    description: str = Field(..., description="Issue description")
    issue_type: str = Field(..., description="Issue type (Bug, Task, Story, etc.)")


class TransitionIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key")
    transition_id: str = Field(..., description="Transition ID")


@server.list_tools()
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


def get_auth_header() -> str:
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not jira_email or not jira_api_token:
        raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN must be configured")

    credentials = f"{jira_email}:{jira_api_token}"
    encoded = b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    jira_domain = os.getenv("JIRA_DOMAIN")
    if not jira_domain:
        return [TextContent(type="text", text="Error: JIRA_DOMAIN not configured")]

    try:
        auth_header = get_auth_header()
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    base_url = f"https://{jira_domain}/rest/api/3"

    async with httpx.AsyncClient() as client:
        if name == "jira_add_comment":
            validated_input = AddCommentInput.model_validate(arguments)

            url = f"{base_url}/issue/{validated_input.issue_key}/comment"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"body": validated_input.comment},
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "jira_comment_added",
                    issue_key=validated_input.issue_key,
                    comment_id=result.get("id"),
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added comment to {validated_input.issue_key}. Comment ID: {result.get('id')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "jira_comment_failed",
                    issue_key=validated_input.issue_key,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error adding comment: {str(e)}")]

        elif name == "jira_get_issue":
            validated_input = GetIssueInput.model_validate(arguments)

            url = f"{base_url}/issue/{validated_input.issue_key}"

            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()

                result = response.json()
                fields = result.get("fields", {})

                return [
                    TextContent(
                        type="text",
                        text=f"Issue {validated_input.issue_key}:\nSummary: {fields.get('summary')}\nStatus: {fields.get('status', {}).get('name')}\nDescription: {fields.get('description')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "jira_get_issue_failed",
                    issue_key=validated_input.issue_key,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error getting issue: {str(e)}")]

        elif name == "jira_create_issue":
            validated_input = CreateIssueInput.model_validate(arguments)

            url = f"{base_url}/issue"

            payload = {
                "fields": {
                    "project": {"key": validated_input.project_key},
                    "summary": validated_input.summary,
                    "description": validated_input.description,
                    "issuetype": {"name": validated_input.issue_type},
                }
            }

            try:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=30.0
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "jira_issue_created",
                    issue_key=result.get("key"),
                    project=validated_input.project_key,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully created issue {result.get('key')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "jira_create_issue_failed",
                    project=validated_input.project_key,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error creating issue: {str(e)}")]

        elif name == "jira_transition_issue":
            validated_input = TransitionIssueInput.model_validate(arguments)

            url = f"{base_url}/issue/{validated_input.issue_key}/transitions"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"transition": {"id": validated_input.transition_id}},
                    timeout=30.0,
                )
                response.raise_for_status()

                logger.info(
                    "jira_issue_transitioned",
                    issue_key=validated_input.issue_key,
                    transition_id=validated_input.transition_id,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully transitioned {validated_input.issue_key}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "jira_transition_failed",
                    issue_key=validated_input.issue_key,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error transitioning issue: {str(e)}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
