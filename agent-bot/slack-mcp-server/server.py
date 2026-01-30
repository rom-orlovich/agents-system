import os
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

server = Server("slack-mcp-server")


class PostMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID (e.g., C1234567890)", min_length=1)
    text: str = Field(..., description="Message text", min_length=1)
    thread_ts: str | None = Field(None, description="Thread timestamp to reply in thread")


class UpdateMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    ts: str = Field(..., description="Message timestamp to update", min_length=1)
    text: str = Field(..., description="New message text", min_length=1)


class AddReactionInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    timestamp: str = Field(..., description="Message timestamp", min_length=1)
    reaction: str = Field(..., description="Reaction name (e.g., thumbsup, eyes)", min_length=1)


@server.list_tools()
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
            description="Add an emoji reaction to a message",
            inputSchema=AddReactionInput.model_json_schema(),
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        return [TextContent(type="text", text="Error: SLACK_BOT_TOKEN not configured")]

    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        if name == "slack_post_message":
            validated_input = PostMessageInput.model_validate(arguments)

            payload = {
                "channel": validated_input.channel,
                "text": validated_input.text,
            }

            if validated_input.thread_ts:
                payload["thread_ts"] = validated_input.thread_ts

            try:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()

                if not result.get("ok"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(
                        "slack_post_failed",
                        channel=validated_input.channel,
                        error=error_msg,
                    )
                    return [TextContent(type="text", text=f"Error posting message: {error_msg}")]

                logger.info(
                    "slack_message_posted",
                    channel=validated_input.channel,
                    ts=result.get("ts"),
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully posted message to {validated_input.channel}. Timestamp: {result.get('ts')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "slack_post_failed",
                    channel=validated_input.channel,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error posting message: {str(e)}")]

        elif name == "slack_update_message":
            validated_input = UpdateMessageInput.model_validate(arguments)

            try:
                response = await client.post(
                    "https://slack.com/api/chat.update",
                    headers=headers,
                    json={
                        "channel": validated_input.channel,
                        "ts": validated_input.ts,
                        "text": validated_input.text,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()

                if not result.get("ok"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(
                        "slack_update_failed",
                        channel=validated_input.channel,
                        error=error_msg,
                    )
                    return [TextContent(type="text", text=f"Error updating message: {error_msg}")]

                logger.info(
                    "slack_message_updated",
                    channel=validated_input.channel,
                    ts=validated_input.ts,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated message in {validated_input.channel}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "slack_update_failed",
                    channel=validated_input.channel,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error updating message: {str(e)}")]

        elif name == "slack_add_reaction":
            validated_input = AddReactionInput.model_validate(arguments)

            try:
                response = await client.post(
                    "https://slack.com/api/reactions.add",
                    headers=headers,
                    json={
                        "channel": validated_input.channel,
                        "timestamp": validated_input.timestamp,
                        "name": validated_input.reaction,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()

                if not result.get("ok"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(
                        "slack_reaction_failed",
                        channel=validated_input.channel,
                        error=error_msg,
                    )
                    return [TextContent(type="text", text=f"Error adding reaction: {error_msg}")]

                logger.info(
                    "slack_reaction_added",
                    channel=validated_input.channel,
                    reaction=validated_input.reaction,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added :{validated_input.reaction}: reaction",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "slack_reaction_failed",
                    channel=validated_input.channel,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error adding reaction: {str(e)}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
