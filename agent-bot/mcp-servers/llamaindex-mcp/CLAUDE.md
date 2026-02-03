# LlamaIndex MCP Development Guide

## Overview

This is a thin MCP (Model Context Protocol) wrapper around the LlamaIndex service. It exposes the service's capabilities as tools that Claude Code CLI can invoke.

## Key Principles

1. **Thin Wrapper** - No business logic, just protocol translation
2. **Passthrough Design** - All parameters passed directly to backend
3. **Formatted Output** - Results formatted for LLM consumption

## Structure

```
llamaindex-mcp/
├── llamaindex_mcp.py  # Tool definitions
├── main.py            # Server entry point
├── config.py          # Settings
├── Dockerfile
└── requirements.txt
```

## Adding a New Tool

1. Add tool function in `llamaindex_mcp.py`:
   ```python
   @mcp.tool()
   async def new_tool(param: str, org_id: str) -> str:
       """Tool description for Claude."""
       async with httpx.AsyncClient() as client:
           response = await client.post(
               f"{settings.llamaindex_url}/new-endpoint",
               json={"param": param, "org_id": org_id},
           )
           response.raise_for_status()
       return format_result(response.json())
   ```

2. Ensure corresponding endpoint exists in LlamaIndex service

## Important Notes

- Tool docstrings become the tool description Claude sees
- Parameter descriptions in docstrings help Claude understand usage
- Output should be markdown-formatted for readability
- Keep timeout values appropriate for expected response times

## Testing Locally

```bash
# Start LlamaIndex service first
docker-compose --profile knowledge up llamaindex-service

# Then start MCP server
python main.py

# Test with curl
curl http://localhost:9006/sse
```

## File Size

This server should remain small. If adding significant logic, consider:
- Adding to LlamaIndex service instead
- Creating a separate utility module
