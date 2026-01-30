"""Sentry MCP Server using FastMCP."""

import os
from typing import Any
from fastmcp import FastMCP
import httpx

SENTRY_AUTH_TOKEN = os.getenv("SENTRY_AUTH_TOKEN", "")
BASE_URL = "https://sentry.io/api/0"

mcp = FastMCP("Sentry MCP Server")


@mcp.tool()
async def get_issue(issue_id: str) -> dict[str, Any]:
    """Get Sentry issue by ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/issues/{issue_id}/",
            headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def search_issues(organization: str, project: str, query: str | None = None) -> dict[str, Any]:
    """Search issues in a Sentry project."""
    async with httpx.AsyncClient() as client:
        params = {"project": project}
        if query:
            params["query"] = query

        response = await client.get(
            f"{BASE_URL}/organizations/{organization}/issues/",
            headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
            params=params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def update_issue(issue_id: str, status: str | None = None, assigned_to: str | None = None) -> dict[str, Any]:
    """Update Sentry issue status or assignee."""
    async with httpx.AsyncClient() as client:
        payload: dict[str, Any] = {}
        if status:
            payload["status"] = status
        if assigned_to:
            payload["assignedTo"] = assigned_to

        response = await client.put(
            f"{BASE_URL}/issues/{issue_id}/",
            headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_events(issue_id: str, limit: int = 10) -> dict[str, Any]:
    """Get events for a Sentry issue."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/issues/{issue_id}/events/",
            headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def create_comment(issue_id: str, text: str) -> dict[str, Any]:
    """Create a comment on a Sentry issue."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/issues/{issue_id}/notes/",
            headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"},
            json={"text": text},
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(transport="sse", port=int(os.getenv("PORT", 9004)))
