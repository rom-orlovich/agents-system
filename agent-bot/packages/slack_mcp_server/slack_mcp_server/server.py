import os
from mcp.server import Server
from mcp.types import Tool, TextContent
import structlog

from slack_client import (
    SlackClient,
    PostMessageInput,
    UpdateMessageInput,
    AddReactionInput,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

mcp_server = Server("slack-mcp-server")


def get_slack_client() -> SlackClient:
    bot_token = os.getenv("SLACK_BOT_TOKEN")

    if not bot_token:
        raise ValueError("SLACK_BOT_TOKEN must be configured")

    return SlackClient(bot_token=bot_token)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="slack_post_message",
            description="Post a message to a Slack channel",
            inputSchema=PostMessageInput.model_json_schema(),
        ),
        Tool(
            name="slack_update_message",
            description="Update an existing Slack message",
            inputSchema=UpdateMessageInput.model_json_schema(),
        ),
        Tool(
            name="slack_add_reaction",
            description="Add a reaction to a Slack message",
            inputSchema=AddReactionInput.model_json_schema(),
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    client = get_slack_client()

    if name == "slack_post_message":
        validated_input = PostMessageInput.model_validate(arguments)
        result = await client.post_message(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "slack_update_message":
        validated_input = UpdateMessageInput.model_validate(arguments)
        result = await client.update_message(validated_input)
        return [TextContent(type="text", text=result.message)]

    elif name == "slack_add_reaction":
        validated_input = AddReactionInput.model_validate(arguments)
        result = await client.add_reaction(validated_input)
        return [TextContent(type="text", text=result.message)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
