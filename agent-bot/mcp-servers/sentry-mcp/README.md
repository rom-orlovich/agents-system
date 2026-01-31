# Sentry MCP Server

> FastMCP-based MCP server for Sentry operations.

## Purpose

The Sentry MCP server provides a Model Context Protocol interface for Sentry operations. It translates MCP tool calls into HTTP requests to the Sentry API service, keeping credentials isolated.

## Architecture

```
Agent Engine (via mcp.json)
         │
         │ SSE Connection
         ▼
┌─────────────────────────────────────┐
│      Sentry MCP :9004               │
│                                     │
│  1. Receive MCP tool call          │
│  2. Translate to HTTP request       │
│  3. Call sentry-api service        │
│     (no credentials)                │
│  4. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTP (no credentials)
         ▼
┌─────────────────────────────────────┐
│      Sentry API Service            │
│  (Has credentials, makes API call)  │
└─────────────────────────────────────┘
```

## Folder Structure

```
sentry-mcp/
├── main.py                    # FastMCP server entry point
├── sentry_mcp.py              # MCP tool definitions
├── config.py                  # Configuration
└── requirements.txt            # Dependencies
```

## Business Logic

### Core Responsibilities

1. **MCP Tool Exposure**: Expose Sentry operations as MCP tools
2. **Protocol Translation**: Translate MCP calls to HTTP API requests
3. **Credential Isolation**: Never store credentials (delegate to sentry-api service)
4. **SSE Transport**: Provide Server-Sent Events transport for MCP
5. **Error Tracking**: Provide error and issue management

## MCP Tools

### get_issue

Get Sentry issue details.

**Input**:

```json
{
  "issue_id": "1234567890"
}
```

**Output**:

```json
{
  "id": "1234567890",
  "title": "Error: Something went wrong",
  "level": "error",
  "status": "unresolved",
  "count": 42,
  "lastSeen": "2026-01-31T12:00:00Z"
}
```

### list_issues

List issues for a project.

**Input**:

```json
{
  "project": "my-project",
  "status": "unresolved"
}
```

**Output**:

```json
{
  "issues": [
    {
      "id": "1234567890",
      "title": "Error: Something went wrong",
      "level": "error"
    }
  ]
}
```

### update_issue

Update issue status or assignee.

**Input**:

```json
{
  "issue_id": "1234567890",
  "status": "resolved"
}
```

**Output**:

```json
{
  "success": true,
  "status": "resolved"
}
```

## Environment Variables

```bash
SENTRY_API_URL=http://sentry-api:3004
PORT=9004
LOG_LEVEL=INFO
```

## SSE Endpoint

MCP clients connect via Server-Sent Events:

```
GET /sse HTTP/1.1
Host: sentry-mcp:9004
Accept: text/event-stream
```

## Health Check

```bash
curl http://localhost:9004/health
```

## Related Services

- **sentry-api**: Provides actual Sentry API operations
- **agent-engine**: Connects to this MCP server via SSE
