# LlamaIndex MCP Server

MCP (Model Context Protocol) server that exposes LlamaIndex service tools for Claude Code CLI and other MCP clients.

## Quick Start

```bash
# Run with Docker (recommended)
docker-compose --profile knowledge up llamaindex-mcp

# Run locally
cd mcp-servers/llamaindex-mcp
pip install -r requirements.txt
python main.py
```

## Architecture

This is a thin MCP wrapper around the LlamaIndex service:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ SSE (MCP Protocol)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LlamaIndex MCP Server                         │
│                        (port 9006)                               │
│                                                                  │
│  • knowledge_query()     - Hybrid search                         │
│  • code_search()         - Code-specific search                  │
│  • find_related_code()   - Graph relationships                   │
│  • search_jira_tickets() - Jira ticket search                    │
│  • search_confluence()   - Confluence doc search                 │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LlamaIndex Service                            │
│                        (port 8002)                               │
└─────────────────────────────────────────────────────────────────┘
```

## Available Tools

### knowledge_query
Hybrid search across all knowledge sources (code, Jira, Confluence).

```
knowledge_query(
    query: str,         # Natural language query
    org_id: str,        # Organization ID
    source_types: str,  # "code,jira,confluence"
    top_k: int          # Number of results (default: 10)
)
```

### code_search
Search specifically in code repositories.

```
code_search(
    query: str,         # Code or natural language query
    org_id: str,        # Organization ID
    repo_filter: str,   # Repository glob pattern
    language: str,      # Programming language filter
    top_k: int
)
```

### find_related_code
Find code entities related via graph relationships.

```
find_related_code(
    entity: str,        # Entity name (function, class)
    entity_type: str,   # "function", "class", "module", "file"
    org_id: str,
    relationship: str   # "calls", "imports", "extends", "all"
)
```

### search_jira_tickets
Search Jira tickets using semantic search.

```
search_jira_tickets(
    query: str,
    org_id: str,
    project: str,       # Project key filter
    status: str,        # Status filter
    top_k: int
)
```

### search_confluence
Search Confluence documentation.

```
search_confluence(
    query: str,
    org_id: str,
    space: str,         # Space key filter
    top_k: int
)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMAINDEX_URL` | `http://llamaindex-service:8002` | LlamaIndex service URL |
| `MCP_PORT` | `9006` | MCP server port |

## Adding to Claude Code

Add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "llamaindex": {
      "url": "http://llamaindex-mcp:9006/sse",
      "transport": "sse"
    }
  }
}
```

## Replacing the Backend

The MCP server is designed to be backend-agnostic. To use a different knowledge service:

1. Create a new service implementing the same endpoints
2. Update `LLAMAINDEX_URL` to point to your service
3. No changes to MCP server required
