# Slack MCP Server

> FastMCP-based MCP server for Slack operations.

## Purpose

The Slack MCP server provides a Model Context Protocol interface for Slack operations. It translates MCP tool calls into HTTP requests to the Slack API service, keeping credentials isolated.

## Architecture

```
Agent Engine (via mcp.json)
         │
         │ SSE Connection
         ▼
┌─────────────────────────────────────┐
│      Slack MCP :9003                │
│                                     │
│  1. Receive MCP tool call          │
│  2. Translate to HTTP request       │
│  3. Call slack-api service         │
│     (no credentials)                │
│  4. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTP (no credentials)
         ▼
┌─────────────────────────────────────┐
│      Slack API Service             │
│  (Has credentials, makes API call)  │
└─────────────────────────────────────┘
```

## Folder Structure

```
slack-mcp/
├── main.py                    # FastMCP server entry point
├── slack_mcp.py               # MCP tool definitions
├── config.py                  # Configuration
└── requirements.txt            # Dependencies
```

## Business Logic

### Core Responsibilities

1. **MCP Tool Exposure**: Expose Slack operations as MCP tools
2. **Protocol Translation**: Translate MCP calls to HTTP API requests
3. **Credential Isolation**: Never store credentials (delegate to slack-api service)
4. **SSE Transport**: Provide Server-Sent Events transport for MCP
5. **Thread Management**: Handle Slack thread context

## MCP Tools

### post_message

Post a message to a channel or thread.

**Input**:

```json
{
  "channel": "C1234567890",
  "text": "Message text",
  "thread_ts": "1234567890.123456"
}
```

**Output**:

```json
{
  "ts": "1234567890.123457",
  "channel": "C1234567890",
  "text": "Message text"
}
```

### get_channel_history

Get message history for a channel.

**Input**:

```json
{
  "channel": "C1234567890",
  "limit": 100
}
```

**Output**:

```json
{
  "messages": [
    {
      "ts": "1234567890.123456",
      "text": "Message text",
      "user": "U1234567890"
    }
  ]
}
```

### add_reaction

Add emoji reaction to a message.

**Input**:

```json
{
  "channel": "C1234567890",
  "timestamp": "1234567890.123456",
  "name": "eyes"
}
```

**Output**:

```json
{
  "success": true
}
```

### get_user_info

Get user information.

**Input**:

```json
{
  "user_id": "U1234567890"
}
```

**Output**:

```json
{
  "id": "U1234567890",
  "name": "username",
  "real_name": "Real Name"
}
```

## Environment Variables

```bash
SLACK_API_URL=http://slack-api:3003
PORT=9003
LOG_LEVEL=INFO
```

## SSE Endpoint

MCP clients connect via Server-Sent Events:

```
GET /sse HTTP/1.1
Host: slack-mcp:9003
Accept: text/event-stream
```

## Health Check

```bash
curl http://localhost:9003/health
```

## Related Services

- **slack-api**: Provides actual Slack API operations
- **agent-engine**: Connects to this MCP server via SSE
