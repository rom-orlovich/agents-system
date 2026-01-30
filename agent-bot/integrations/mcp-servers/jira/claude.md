# Jira MCP Server - Claude Configuration

## Component Overview

MCP server providing Jira tools for AI agents via stdio protocol.

## Purpose

- 🔧 Expose Jira operations as MCP tools
- 🤖 Used by agent-container via stdio
- 🔄 Uses jira_client package (DRY)
- 📡 FastMCP for tool definitions

## Key Rules

- ❌ NO file > 300 lines
- ❌ NO `any` types
- ✅ Depends on `packages/jira_client`
- ✅ FastMCP for server implementation

## Directory Structure

```
jira/
├── jira_mcp_server/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   └── server.py        # MCP tools (< 300 lines)
├── Dockerfile
├── pyproject.toml
└── claude.md
```

## Tools Provided

### jira_add_comment
```python
{
    "issue_key": "PROJ-123",
    "comment": "Comment text"
}
```

### jira_get_issue
```python
{
    "issue_key": "PROJ-123"
}
```

### jira_create_issue
```python
{
    "project_key": "PROJ",
    "summary": "Issue title",
    "description": "Issue description",
    "issue_type": "Bug"
}
```

### jira_transition_issue
```python
{
    "issue_key": "PROJ-123",
    "transition_id": "31"
}
```

## Implementation

### Server Setup
```python
from mcp.server.stdio import stdio_server
from fastmcp import FastMCP

mcp = FastMCP("Jira MCP Server")

@mcp.tool()
async def jira_add_comment(issue_key: str, comment: str) -> str:
    from jira_client import JiraClient, AddCommentInput

    client = JiraClient(...)
    input_data = AddCommentInput(issue_key=issue_key, comment=comment)
    response = await client.add_comment(input_data)

    return response.message
```

### Entry Point
```python
import asyncio
from mcp.server.stdio import stdio_server
from .server import mcp_server

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

## Environment Variables

```bash
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=your-token
JIRA_DOMAIN=your-domain.atlassian.net
```

## Usage from Agent

```python
# Agent calls MCP tool
result = await mcp_client.call_tool(
    name="jira_add_comment",
    arguments={
        "issue_key": "PROJ-123",
        "comment": "Agent comment"
    }
)
```

## Testing

```python
@pytest.mark.asyncio
async def test_jira_add_comment_tool(mock_jira_client):
    result = await jira_add_comment("PROJ-123", "Test comment")
    assert "success" in result.lower()
```

## Docker

### Build
```bash
docker build -f integrations/mcp-servers/jira/Dockerfile -t jira-mcp-server .
```

### Run
```bash
docker run -i --env-file .env jira-mcp-server
```

## Dependencies

- jira_client (from packages/)
- fastmcp
- mcp

## Summary

- 🔧 MCP interface for Jira
- 📡 stdio protocol
- 🔄 Uses shared jira_client
- ✅ < 300 lines
- ✅ NO `any` types
