from typing import Any
from fastmcp import FastMCP

from slack_mcp import SlackAPI
from config import get_settings

mcp = FastMCP("Slack MCP Server")
slack_api = SlackAPI()


@mcp.tool()
async def send_slack_message(
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """
    Send a message to a Slack channel.

    Args:
        channel: Channel ID or name (e.g., C1234567890 or #general)
        text: Message text to send
        thread_ts: Optional thread timestamp to reply in a thread

    Returns:
        Message details including the timestamp
    """
    return await slack_api.send_message(channel, text, thread_ts)


@mcp.tool()
async def get_slack_channel_history(
    channel: str,
    limit: int = 100,
    oldest: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    """
    Get message history from a Slack channel.

    Args:
        channel: Channel ID
        limit: Maximum number of messages to return
        oldest: Only messages after this timestamp
        latest: Only messages before this timestamp

    Returns:
        List of messages in the channel
    """
    return await slack_api.get_channel_history(channel, limit, oldest, latest)


@mcp.tool()
async def get_slack_thread(
    channel: str, thread_ts: str, limit: int = 100
) -> dict[str, Any]:
    """
    Get replies in a Slack thread.

    Args:
        channel: Channel ID
        thread_ts: Thread parent message timestamp
        limit: Maximum number of replies to return

    Returns:
        List of messages in the thread
    """
    return await slack_api.get_thread_replies(channel, thread_ts, limit)


@mcp.tool()
async def add_slack_reaction(
    channel: str, timestamp: str, emoji: str
) -> dict[str, Any]:
    """
    Add an emoji reaction to a Slack message.

    Args:
        channel: Channel ID
        timestamp: Message timestamp
        emoji: Emoji name without colons (e.g., 'thumbsup')

    Returns:
        Success status
    """
    return await slack_api.add_reaction(channel, timestamp, emoji)


@mcp.tool()
async def get_slack_channel_info(channel: str) -> dict[str, Any]:
    """
    Get information about a Slack channel.

    Args:
        channel: Channel ID

    Returns:
        Channel details including name, topic, and members
    """
    return await slack_api.get_channel_info(channel)


@mcp.tool()
async def list_slack_channels(
    limit: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    """
    List all Slack channels in the workspace.

    Args:
        limit: Maximum number of channels to return
        cursor: Pagination cursor for next page

    Returns:
        List of channels
    """
    return await slack_api.list_channels(limit, cursor)


@mcp.tool()
async def get_slack_user_info(user_id: str) -> dict[str, Any]:
    """
    Get information about a Slack user.

    Args:
        user_id: User ID (e.g., U1234567890)

    Returns:
        User details including name, email, and status
    """
    return await slack_api.get_user_info(user_id)


@mcp.tool()
async def update_slack_message(
    channel: str,
    ts: str,
    text: str,
) -> dict[str, Any]:
    """
    Update an existing Slack message.

    Args:
        channel: Channel ID
        ts: Message timestamp
        text: New message text

    Returns:
        Updated message details
    """
    return await slack_api.update_message(channel, ts, text)


if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", port=settings.port)
