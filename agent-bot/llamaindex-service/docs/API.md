# LlamaIndex Service API Reference

## Base URL

```
http://localhost:8002
```

## Endpoints

### Health Check

```
GET /health
```

Returns service health status and connected components.

**Response:**
```json
{
  "status": "healthy",
  "vector_store": "connected",
  "graph_store": "connected",
  "cache": "connected",
  "collections": ["code", "jira_tickets", "confluence_docs"]
}
```

Status values:
- `healthy` - All components operational
- `degraded` - Vector store works, optional components failed
- `unhealthy` - Vector store unavailable

---

### Hybrid Query

```
POST /query
```

Execute semantic search across multiple knowledge sources.

**Request:**
```json
{
  "query": "order processing authentication",
  "org_id": "my-org",
  "source_types": ["code", "jira", "confluence"],
  "top_k": 10,
  "include_metadata": true
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "def process_order(order_id, user): ...",
      "source_type": "code",
      "source_id": "api-service/orders.py:42",
      "relevance_score": 0.95,
      "metadata": {
        "repo": "api-service",
        "language": "python",
        "name": "process_order"
      }
    }
  ],
  "query": "order processing authentication",
  "total_results": 15,
  "source_types_queried": ["code", "jira", "confluence"],
  "cached": false,
  "query_time_ms": 125.5
}
```

---

### Code Query

```
POST /query/code
```

Search specifically in code repositories.

**Request:**
```json
{
  "query": "authentication middleware",
  "org_id": "my-org",
  "repo_filter": "api-service",
  "language": "python",
  "top_k": 10
}
```

**Parameters:**
- `repo_filter` - Filter by repository name (default: "*" for all)
- `language` - Filter by programming language (default: "*" for all)

---

### Ticket Query

```
POST /query/tickets
```

Search Jira tickets.

**Request:**
```json
{
  "query": "authentication bug login",
  "org_id": "my-org",
  "project": "AUTH",
  "status": "Open",
  "top_k": 10
}
```

**Parameters:**
- `project` - Filter by Jira project key (default: "*" for all)
- `status` - Filter by issue status (default: "*" for all)

---

### Documentation Query

```
POST /query/docs
```

Search Confluence documentation.

**Request:**
```json
{
  "query": "API authentication guide",
  "org_id": "my-org",
  "space": "ENG",
  "top_k": 10
}
```

**Parameters:**
- `space` - Filter by Confluence space key (default: "*" for all)

---

### Graph Related Entities

```
POST /graph/related
```

Find code entities related to a given entity via graph relationships.

**Request:**
```json
{
  "entity": "process_order",
  "entity_type": "function",
  "org_id": "my-org",
  "relationship": "all"
}
```

**Entity Types:**
- `function` - Function/method
- `class` - Class definition
- `module` - Python module
- `file` - Source file

**Relationship Types:**
- `all` - All relationships
- `calls` - Functions called by entity
- `called_by` - Functions that call entity
- `imports` - Modules imported
- `imported_by` - Modules that import

**Response:**
```json
{
  "entity": "process_order",
  "entity_type": "function",
  "relationships": {
    "calls": [
      {
        "name": "validate_order",
        "entity_type": "function",
        "file_path": "validators.py",
        "line_number": 15
      }
    ],
    "called_by": [
      {
        "name": "handle_request",
        "entity_type": "function",
        "file_path": "handlers.py",
        "line_number": 50
      }
    ]
  }
}
```

---

### List Collections

```
GET /collections
```

List available vector store collections.

**Response:**
```json
["code", "jira_tickets", "confluence_docs", "github_issues"]
```

---

## Error Responses

All endpoints return standard error format:

```json
{
  "detail": "Error message describing the issue"
}
```

**Status Codes:**
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `503` - Service unavailable (dependencies not ready)
- `500` - Internal server error
