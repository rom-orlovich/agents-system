"""Slack MCP Server using FastMCP."""

import os
from typing import Any
from fastmcp import FastMCP
import httpx

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
BASE_URL = "https://slack.com/api"

mcp = FastMCP("Slack MCP Server")


@mcp.tool()
async def send_message(channel: str, text: str, thread_ts: str | None = None) -> dict[str, Any]:
    """Send a message to a Slack channel."""
    async with httpx.AsyncClient() as client:
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = await client.post(
            f"{BASE_URL}/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json=payload,
        )
        return response.json()


@mcp.tool()
async def get_channel_history(channel: str, limit: int = 100) -> dict[str, Any]:
    """Get message history from a Slack channel."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/conversations.history",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"channel": channel, "limit": limit},
        )
        return response.json()


@mcp.tool()
async def upload_file(channels: list[str], file_path: str, title: str | None = None) -> dict[str, Any]:
    """Upload a file to Slack channels."""
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"channels": ",".join(channels)}
            if title:
                data["title"] = title

            response = await client.post(
                f"{BASE_URL}/files.upload",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                data=data,
                files=files,
            )
        return response.json()


@mcp.tool()
async def add_reaction(channel: str, timestamp: str, reaction: str) -> dict[str, Any]:
    """Add a reaction emoji to a message."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/reactions.add",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": channel, "timestamp": timestamp, "name": reaction},
        )
        return response.json()


if __name__ == "__main__":
    mcp.run(transport="sse", port=int(os.getenv("PORT", 9003)))
