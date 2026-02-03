# GKG MCP Server

MCP (Model Context Protocol) server that exposes GitLab Knowledge Graph service tools for Claude Code CLI and other MCP clients.

## Quick Start

```bash
# Run with Docker (recommended)
docker-compose --profile knowledge up gkg-mcp

# Run locally
cd mcp-servers/gkg-mcp
pip install -r requirements.txt
python main.py
```

## Architecture

This is a thin MCP wrapper around the GKG service:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ SSE (MCP Protocol)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GKG MCP Server                             │
│                        (port 9007)                               │
│                                                                  │
│  • analyze_dependencies()  - File dependency analysis            │
│  • find_usages()           - Symbol usage search                 │
│  • get_call_graph()        - Function call relationships         │
│  • get_class_hierarchy()   - Class inheritance                   │
│  • get_related_entities()  - General relationship queries        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GKG Service                                │
│                        (port 8003)                               │
└─────────────────────────────────────────────────────────────────┘
```

## Available Tools

### analyze_dependencies
Analyze import/dependency relationships of a file.

```
analyze_dependencies(
    file_path: str,     # Path to the file
    org_id: str,        # Organization ID
    repo: str,          # Repository name
    depth: int          # Traversal depth (default: 3)
)
```

### find_usages
Find all usages of a symbol across the codebase.

```
find_usages(
    symbol: str,        # Symbol name (function, class, variable)
    org_id: str,        # Organization ID
    repo: str           # Repository filter
)
```

### get_call_graph
Get function call relationships (callers and callees).

```
get_call_graph(
    function_name: str,
    org_id: str,
    repo: str,
    direction: str,     # "callers", "callees", or "both"
    depth: int          # Traversal depth
)
```

### get_class_hierarchy
Get class inheritance hierarchy (parents and children).

```
get_class_hierarchy(
    class_name: str,
    org_id: str,
    repo: str
)
```

### get_related_entities
Find entities related to a specific code entity.

```
get_related_entities(
    entity: str,        # Entity name
    entity_type: str,   # "function", "class", "module", "file"
    org_id: str,
    relationship: str   # "calls", "imports", "extends", "references", "all"
)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GKG_URL` | `http://gkg-service:8003` | GKG service URL |
| `MCP_PORT` | `9007` | MCP server port |

## Adding to Claude Code

Add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "gkg": {
      "url": "http://gkg-mcp:9007/sse",
      "transport": "sse"
    }
  }
}
```

## Replacing the Backend

The MCP server is backend-agnostic. To use a different graph store:

1. Create a service implementing the same endpoints
2. Update `GKG_URL` to point to your service
3. No changes to MCP server required
