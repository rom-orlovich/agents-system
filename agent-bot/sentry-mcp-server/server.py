import os
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

server = Server("sentry-mcp-server")


class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    comment: str = Field(..., description="Comment text", min_length=1)


class UpdateIssueStatusInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    status: Literal["resolved", "unresolved", "ignored"] = Field(
        ..., description="New status for the issue"
    )


class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)


class AssignIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    assignee: str = Field(..., description="User email or username", min_length=1)


class AddTagInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    key: str = Field(..., description="Tag key", min_length=1)
    value: str = Field(..., description="Tag value", min_length=1)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="sentry_add_comment",
            description="Add a comment to a Sentry issue",
            inputSchema=AddCommentInput.model_json_schema(),
        ),
        Tool(
            name="sentry_update_status",
            description="Update the status of a Sentry issue (resolve, ignore, unresolve)",
            inputSchema=UpdateIssueStatusInput.model_json_schema(),
        ),
        Tool(
            name="sentry_get_issue",
            description="Get details of a Sentry issue",
            inputSchema=GetIssueInput.model_json_schema(),
        ),
        Tool(
            name="sentry_assign_issue",
            description="Assign a Sentry issue to a user",
            inputSchema=AssignIssueInput.model_json_schema(),
        ),
        Tool(
            name="sentry_add_tag",
            description="Add a tag to a Sentry issue",
            inputSchema=AddTagInput.model_json_schema(),
        ),
    ]


def get_auth_header() -> str:
    auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    if not auth_token:
        raise ValueError("SENTRY_AUTH_TOKEN not configured")
    return f"Bearer {auth_token}"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    sentry_org = os.getenv("SENTRY_ORG")
    sentry_project = os.getenv("SENTRY_PROJECT")

    if not sentry_org:
        return [TextContent(type="text", text="Error: SENTRY_ORG not configured")]

    try:
        auth_header = get_auth_header()
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }

    base_url = "https://sentry.io/api/0"

    async with httpx.AsyncClient() as client:
        if name == "sentry_add_comment":
            validated_input = AddCommentInput.model_validate(arguments)

            url = f"{base_url}/issues/{validated_input.issue_id}/comments/"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"text": validated_input.comment},
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "sentry_comment_added",
                    issue_id=validated_input.issue_id,
                    comment_id=result.get("id"),
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added comment to issue {validated_input.issue_id}. Comment ID: {result.get('id')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_comment_failed",
                    issue_id=validated_input.issue_id,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error adding comment: {str(e)}")]

        elif name == "sentry_update_status":
            validated_input = UpdateIssueStatusInput.model_validate(arguments)

            url = f"{base_url}/issues/{validated_input.issue_id}/"

            try:
                response = await client.put(
                    url,
                    headers=headers,
                    json={"status": validated_input.status},
                    timeout=30.0,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_status_updated",
                    issue_id=validated_input.issue_id,
                    status=validated_input.status,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated issue {validated_input.issue_id} to {validated_input.status}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_status_update_failed",
                    issue_id=validated_input.issue_id,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error updating status: {str(e)}")]

        elif name == "sentry_get_issue":
            validated_input = GetIssueInput.model_validate(arguments)

            url = f"{base_url}/issues/{validated_input.issue_id}/"

            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()

                result = response.json()

                issue_info = f"""Issue {validated_input.issue_id}:
Title: {result.get('title')}
Status: {result.get('status')}
Level: {result.get('level')}
Culprit: {result.get('culprit')}
Count: {result.get('count')} events
First Seen: {result.get('firstSeen')}
Last Seen: {result.get('lastSeen')}
"""

                logger.info(
                    "sentry_issue_retrieved",
                    issue_id=validated_input.issue_id,
                )

                return [TextContent(type="text", text=issue_info)]
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_get_issue_failed",
                    issue_id=validated_input.issue_id,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error getting issue: {str(e)}")]

        elif name == "sentry_assign_issue":
            validated_input = AssignIssueInput.model_validate(arguments)

            url = f"{base_url}/issues/{validated_input.issue_id}/"

            try:
                response = await client.put(
                    url,
                    headers=headers,
                    json={"assignedTo": validated_input.assignee},
                    timeout=30.0,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_issue_assigned",
                    issue_id=validated_input.issue_id,
                    assignee=validated_input.assignee,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully assigned issue {validated_input.issue_id} to {validated_input.assignee}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_assign_failed",
                    issue_id=validated_input.issue_id,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error assigning issue: {str(e)}")]

        elif name == "sentry_add_tag":
            validated_input = AddTagInput.model_validate(arguments)

            url = f"{base_url}/issues/{validated_input.issue_id}/tags/"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={
                        "key": validated_input.key,
                        "value": validated_input.value,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_tag_added",
                    issue_id=validated_input.issue_id,
                    key=validated_input.key,
                    value=validated_input.value,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added tag {validated_input.key}={validated_input.value} to issue {validated_input.issue_id}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_tag_failed",
                    issue_id=validated_input.issue_id,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error adding tag: {str(e)}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
