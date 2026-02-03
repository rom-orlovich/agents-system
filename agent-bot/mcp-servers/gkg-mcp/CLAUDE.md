# GKG MCP Development Guide

## Overview

This is a thin MCP (Model Context Protocol) wrapper around the GKG (GitLab Knowledge Graph) service. It exposes graph analysis capabilities as tools for Claude Code CLI.

## Key Principles

1. **Thin Wrapper** - No business logic, just protocol translation
2. **Passthrough Design** - All parameters passed directly to backend
3. **Formatted Output** - Results formatted for LLM consumption

## Structure

```
gkg-mcp/
├── gkg_mcp.py         # Tool definitions
├── main.py            # Server entry point
├── config.py          # Settings
├── Dockerfile
└── requirements.txt
```

## Adding a New Tool

1. Add tool function in `gkg_mcp.py`:
   ```python
   @mcp.tool()
   async def new_analysis(
       file_path: str,
       org_id: str,
   ) -> str:
       """Docstring becomes tool description."""
       async with httpx.AsyncClient() as client:
           response = await client.post(
               f"{settings.gkg_url}/new-endpoint",
               json={"file_path": file_path, "org_id": org_id},
           )
           response.raise_for_status()
       return response.json().get("formatted_output", "No results")
   ```

2. Ensure corresponding endpoint exists in GKG service

## Output Formatting

The GKG service returns both raw data and `formatted_output` fields. Use the formatted version for tool responses as it's designed for human/LLM readability.

## Important Notes

- Tool docstrings define how Claude understands the tool
- Keep output markdown-formatted for readability
- Handle empty results gracefully with descriptive messages
- Timeouts should match expected GKG query times

## Testing Locally

```bash
# Start GKG service first
docker-compose --profile knowledge up gkg-service

# Then start MCP server
python main.py

# Test with curl
curl http://localhost:9007/sse
```

## File Size

This server should remain small. Complex logic belongs in GKG service.
