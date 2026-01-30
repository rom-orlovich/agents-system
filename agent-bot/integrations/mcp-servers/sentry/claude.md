# Sentry MCP Server

## Purpose
MCP protocol server for Sentry operations, providing tools for Claude CLI integration.

## Architecture
- **Layer:** MCP Protocol Layer
- **Depends on:** `integrations/packages/sentry_client/`
- **Protocol:** Model Context Protocol (MCP)

## Key Files
- `sentry_mcp_server/server.py` (110 lines): MCP tools implementation
- `sentry_mcp_server/__main__.py`: Entry point

## MCP Tools

### sentry_add_comment
```python
@mcp.tool
async def sentry_add_comment(issue_id: str, comment: str) -> bool:
    """Add comment to Sentry issue."""
```

### sentry_update_status
```python
@mcp.tool
async def sentry_update_status(
    issue_id: str,
    status: Literal["resolved", "ignored", "unresolved"]
) -> bool:
    """Update Sentry issue status."""
```

### sentry_get_issue
```python
@mcp.tool
async def sentry_get_issue(issue_id: str) -> dict:
    """Get Sentry issue details."""
```

## Usage in Claude CLI
```python
# Agent uses these tools automatically
result = await mcp.call_tool(
    "sentry_add_comment",
    {"issue_id": "123", "comment": "Investigating"}
)
```

## Configuration
```bash
SENTRY_AUTH_TOKEN=sntrys_xxx
SENTRY_ORGANIZATION=my-org
MCP_SERVER_NAME=sentry
```

## Integration
Used by `agent-container/core/mcp_client.py` to execute Sentry operations during task processing.
