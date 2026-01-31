# MCP Servers

> Model Context Protocol (MCP) servers that provide standardized interfaces to external services.

## Purpose

MCP Servers implement the Model Context Protocol to provide standardized interfaces for agent-engine to interact with external services. They translate MCP protocol calls into HTTP requests to API services, keeping credentials isolated.

## Architecture

```
Agent Engine (via mcp.json)
         │
         │ SSE Connection
         ▼
┌─────────────────────────────────────┐
│      MCP Server                    │
│                                     │
│  1. Receive MCP tool call          │
│  2. Translate to HTTP request       │
│  3. Call API service (no creds)    │
│  4. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTP (no credentials)
         ▼
┌─────────────────────────────────────┐
│      API Service                    │
│  (Has credentials, makes API call)  │
└─────────────────────────────────────┘
```

## Folder Structure

```
mcp-servers/
├── README.md                 # This file
├── docker-compose.mcp.yml
├── github-mcp/              # Official GitHub MCP
├── jira-mcp/                 # Custom FastMCP
│   ├── main.py
│   ├── jira_mcp.py          # MCP tool definitions
│   └── config.py
├── slack-mcp/                # Custom FastMCP
│   ├── main.py
│   ├── slack_mcp.py
│   └── config.py
├── sentry-mcp/               # Custom FastMCP
│   ├── main.py
│   ├── sentry_mcp.py
│   └── config.py
└── knowledge-graph-mcp/       # Custom FastMCP
    ├── main.py
    ├── kg_client.py
    └── config.py
```

## MCP Servers

| Service             | Port | Type     | Framework        |
| ------------------- | ---- | -------- | ---------------- |
| GitHub MCP          | 9001 | Official | Node.js          |
| Jira MCP            | 9002 | Custom   | FastMCP (Python) |
| Slack MCP           | 9003 | Custom   | FastMCP (Python) |
| Sentry MCP          | 9004 | Custom   | FastMCP (Python) |
| Knowledge Graph MCP | 9005 | Custom   | FastMCP (Python) |

## Security Model

**Key Principle**: MCP servers NEVER store API keys.

- MCP servers call API services via HTTP
- API services have credentials and make actual API calls
- Complete credential isolation

## GitHub MCP

**Purpose**: Official GitHub MCP server implementation.

**Tools Available**:

- `get_issue` - Get issue details
- `create_issue` - Create new issue
- `get_pull_request` - Get PR details
- `create_pull_request` - Create PR
- `get_file_contents` - Get file from repo
- `search_code` - Search code in repo

## Jira MCP

**Purpose**: Custom FastMCP-based Jira MCP server.

**Tools Available**:

- `get_jira_issue` - Get issue details
- `create_jira_issue` - Create issue
- `update_jira_issue` - Update issue
- `post_comment` - Post comment to issue
- `search_issues` - Execute JQL query
- `transition_issue` - Move issue through workflow

## Slack MCP

**Purpose**: Custom FastMCP-based Slack MCP server.

**Tools Available**:

- `post_message` - Post message to channel/thread
- `get_channel_history` - Get message history
- `add_reaction` - Add emoji reaction
- `get_user_info` - Get user information

## Sentry MCP

**Purpose**: Custom FastMCP-based Sentry MCP server.

**Tools Available**:

- `get_issue` - Get Sentry issue details
- `list_issues` - List issues for project
- `update_issue` - Update issue status
- `get_event` - Retrieve event details

## Knowledge Graph MCP

**Purpose**: MCP wrapper for Knowledge Graph service.

**Tools Available**:

- `search_nodes` - Search code entities
- `find_path` - Find path between entities
- `find_neighbors` - Find related entities
- `get_statistics` - Get graph statistics

## Environment Variables

```bash
# API Service URLs (no credentials)
GITHUB_API_URL=http://github-api:3001
JIRA_API_URL=http://jira-api:3002
SLACK_API_URL=http://slack-api:3003
SENTRY_API_URL=http://sentry-api:3004
KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000
```

## SSE Endpoint

MCP clients connect via Server-Sent Events:

```
GET /sse HTTP/1.1
Host: jira-mcp:9002
Accept: text/event-stream
```

## Health Checks

```bash
curl http://localhost:9001/health  # GitHub
curl http://localhost:9002/health  # Jira
curl http://localhost:9003/health  # Slack
curl http://localhost:9004/health  # Sentry
curl http://localhost:9005/health  # Knowledge Graph
```

## Related Services

- **agent-engine**: Connects to MCP servers via SSE
- **api-services**: MCP servers call API services for actual operations
- **knowledge-graph**: Knowledge Graph MCP wraps knowledge-graph service
