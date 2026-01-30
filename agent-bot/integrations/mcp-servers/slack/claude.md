# Slack MCP Server

## Purpose
MCP protocol server for Slack operations, providing tools for Claude CLI integration.

## Architecture
- **Layer:** MCP Protocol Layer
- **Depends on:** `integrations/packages/slack_client/`
- **Protocol:** Model Context Protocol (MCP)

## Key Files
- `slack_mcp_server/server.py` (76 lines): MCP tools implementation
- `slack_mcp_server/__main__.py`: Entry point

## MCP Tools

### slack_post_message
```python
@mcp.tool
async def slack_post_message(
    channel: str,
    text: str,
    thread_ts: str | None = None
) -> bool:
    """Post message to Slack channel."""
```

### slack_update_message
```python
@mcp.tool
async def slack_update_message(
    channel: str,
    ts: str,
    text: str
) -> bool:
    """Update existing Slack message."""
```

### slack_add_reaction
```python
@mcp.tool
async def slack_add_reaction(
    channel: str,
    timestamp: str,
    name: str
) -> bool:
    """Add emoji reaction to message."""
```

## Usage in Claude CLI
```python
# Agent uses these tools automatically
result = await mcp.call_tool(
    "slack_post_message",
    {"channel": "C123", "text": "Task complete ✅"}
)
```

## Configuration
```bash
SLACK_BOT_TOKEN=xoxb-xxx
MCP_SERVER_NAME=slack
```

## Integration
Used by `agent-container/core/mcp_client.py` to execute Slack operations during task processing.
