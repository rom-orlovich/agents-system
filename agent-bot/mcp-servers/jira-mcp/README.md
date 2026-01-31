# Jira MCP Server

> FastMCP-based MCP server for Jira operations.

## Purpose

The Jira MCP server provides a Model Context Protocol interface for Jira operations. It translates MCP tool calls into HTTP requests to the Jira API service, keeping credentials isolated.

## Architecture

```
Agent Engine (via mcp.json)
         │
         │ SSE Connection
         ▼
┌─────────────────────────────────────┐
│      Jira MCP :9002                 │
│                                     │
│  1. Receive MCP tool call          │
│  2. Translate to HTTP request       │
│  3. Call jira-api service          │
│     (no credentials)                │
│  4. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTP (no credentials)
         ▼
┌─────────────────────────────────────┐
│      Jira API Service              │
│  (Has credentials, makes API call)  │
└─────────────────────────────────────┘
```

## Folder Structure

```
jira-mcp/
├── main.py                    # FastMCP server entry point
├── jira_mcp.py                # MCP tool definitions
├── config.py                  # Configuration
└── requirements.txt            # Dependencies
```

## Business Logic

### Core Responsibilities

1. **MCP Tool Exposure**: Expose Jira operations as MCP tools
2. **Protocol Translation**: Translate MCP calls to HTTP API requests
3. **Credential Isolation**: Never store credentials (delegate to jira-api service)
4. **SSE Transport**: Provide Server-Sent Events transport for MCP
5. **Error Handling**: Standardize error responses

## MCP Tools

### get_jira_issue

Get issue details by key.

**Input**:

```json
{
  "issue_key": "PROJ-123"
}
```

**Output**:

```json
{
  "key": "PROJ-123",
  "summary": "Issue title",
  "description": "Issue description",
  "status": "In Progress",
  "assignee": "user@example.com"
}
```

### post_comment

Post a comment to an issue.

**Input**:

```json
{
  "issue_key": "PROJ-123",
  "body": "Comment text"
}
```

**Output**:

```json
{
  "id": "12345",
  "body": "Comment text",
  "created": "2026-01-31T12:00:00Z"
}
```

### search_issues

Execute JQL query to find issues.

**Input**:

```json
{
  "jql": "project=PROJ AND status=Open"
}
```

**Output**:

```json
{
  "issues": [
    {
      "key": "PROJ-123",
      "summary": "Issue title",
      "status": "Open"
    }
  ]
}
```

### transition_issue

Move issue through workflow.

**Input**:

```json
{
  "issue_key": "PROJ-123",
  "transition_id": "21"
}
```

**Output**:

```json
{
  "success": true,
  "new_status": "In Progress"
}
```

## Environment Variables

```bash
JIRA_API_URL=http://jira-api:3002
PORT=9002
LOG_LEVEL=INFO
```

## SSE Endpoint

MCP clients connect via Server-Sent Events:

```
GET /sse HTTP/1.1
Host: jira-mcp:9002
Accept: text/event-stream
```

## Health Check

```bash
curl http://localhost:9002/health
```

## Related Services

- **jira-api**: Provides actual Jira API operations
- **agent-engine**: Connects to this MCP server via SSE
