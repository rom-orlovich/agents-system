# Knowledge Graph MCP Server

> FastMCP-based MCP server wrapper for Knowledge Graph service.

## Purpose

The Knowledge Graph MCP server provides a Model Context Protocol interface for the Knowledge Graph service. It translates MCP tool calls into HTTP requests to the Knowledge Graph service, enabling semantic code search and dependency tracking.

## Architecture

```
Agent Engine (via mcp.json)
         │
         │ SSE Connection
         ▼
┌─────────────────────────────────────┐
│   Knowledge Graph MCP :9005         │
│                                     │
│  1. Receive MCP tool call          │
│  2. Translate to HTTP request       │
│  3. Call knowledge-graph service    │
│  4. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTP
         ▼
┌─────────────────────────────────────┐
│   Knowledge Graph Service :4000    │
│  (Rust-based graph database)       │
└─────────────────────────────────────┘
```

## Folder Structure

```
knowledge-graph-mcp/
├── main.py                    # FastMCP server entry point
├── kg_client.py                # Knowledge Graph client
├── config.py                  # Configuration
└── requirements.txt            # Dependencies
```

## Business Logic

### Core Responsibilities

1. **MCP Tool Exposure**: Expose Knowledge Graph operations as MCP tools
2. **Protocol Translation**: Translate MCP calls to HTTP API requests
3. **Graph Queries**: Provide graph query operations
4. **SSE Transport**: Provide Server-Sent Events transport for MCP
5. **Semantic Search**: Enable semantic code search

## MCP Tools

### search_nodes

Search for code entities (nodes).

**Input**:

```json
{
  "query": "function main",
  "node_type": "Function"
}
```

**Output**:

```json
{
  "nodes": [
    {
      "id": "func:main",
      "name": "main",
      "file_path": "src/main.py",
      "node_type": "Function"
    }
  ]
}
```

### find_path

Find path between two entities.

**Input**:

```json
{
  "source": "func:main",
  "target": "func:helper",
  "max_depth": 5
}
```

**Output**:

```json
{
  "path": [
    { "id": "func:main", "type": "Function" },
    { "id": "func:helper", "type": "Function" }
  ],
  "length": 1
}
```

### find_neighbors

Find neighbors of a node.

**Input**:

```json
{
  "node_id": "func:main",
  "edge_type": "Calls"
}
```

**Output**:

```json
{
  "neighbors": [
    {
      "id": "func:helper",
      "type": "Function",
      "edge_type": "Calls"
    }
  ]
}
```

## Environment Variables

```bash
KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000
PORT=9005
LOG_LEVEL=INFO
```

## SSE Endpoint

MCP clients connect via Server-Sent Events:

```
GET /sse HTTP/1.1
Host: knowledge-graph-mcp:9005
Accept: text/event-stream
```

## Health Check

```bash
curl http://localhost:9005/health
```

## Related Services

- **knowledge-graph**: Rust-based graph database service
- **agent-engine**: Connects to this MCP server via SSE
