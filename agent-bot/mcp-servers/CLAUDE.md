# MCP Servers

> Model Context Protocol servers for external service integration.

## Overview

MCP servers provide standardized tool access to external services. The agent engine connects to these via SSE (Server-Sent Events).

## Containers

| Service | Port | Type | Framework |
|---------|------|------|-----------|
| GitHub MCP | 9001 | Official | Node.js |
| Jira MCP | 9002 | Custom | FastMCP (Python) |
| Slack MCP | 9003 | Custom | FastMCP (Python) |
| Sentry MCP | 9004 | Custom | FastMCP (Python) |

## Architecture

```
Agent Engine
     │
     │ SSE Connections
     ▼
┌─────────────────────────────────────────────────────┐
│                MCP Servers                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │  │
│  │  :9001  │ │  :9002  │ │  :9003  │ │  :9004  │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────┘
     │
     │ HTTP API Calls
     ▼
┌─────────────────────────────────────────────────────┐
│               API Services                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │  │
│  │  :3001  │ │  :3002  │ │  :3003  │ │  :3004  │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────┘
```

## GitHub MCP (Official)

Uses the official `github/github-mcp-server`:

```bash
# Dockerfile
FROM node:20-alpine
RUN npm install -g @anthropic-ai/github-mcp-server
CMD ["github-mcp-server", "--port", "9001"]
```

**Tools Available**:
- `get_issue` - Get issue details
- `create_issue` - Create new issue
- `update_issue` - Update issue
- `get_pull_request` - Get PR details
- `create_pull_request` - Create PR
- `merge_pull_request` - Merge PR
- `get_file_contents` - Get file from repo
- `search_code` - Search code in repo

## Jira MCP (Custom FastMCP)

```python
from fastmcp import FastMCP

mcp = FastMCP("jira-mcp")

@mcp.tool()
async def get_issue(issue_key: str) -> dict:
    """Get Jira issue details."""
    ...

@mcp.tool()
async def post_comment(issue_key: str, comment: str) -> dict:
    """Post comment to Jira issue."""
    ...

@mcp.tool()
async def search_issues(jql: str, max_results: int = 50) -> list[dict]:
    """Search Jira issues using JQL."""
    ...

@mcp.tool()
async def transition_issue(issue_key: str, transition_id: str) -> dict:
    """Transition issue to new status."""
    ...
```

## Slack MCP (Custom FastMCP)

```python
@mcp.tool()
async def post_message(channel: str, text: str, thread_ts: str | None = None) -> dict:
    """Post message to Slack channel."""
    ...

@mcp.tool()
async def get_channel_history(channel: str, limit: int = 100) -> list[dict]:
    """Get channel message history."""
    ...

@mcp.tool()
async def react_to_message(channel: str, timestamp: str, emoji: str) -> dict:
    """Add reaction to message."""
    ...
```

## Sentry MCP (Custom FastMCP)

```python
@mcp.tool()
async def get_issue(issue_id: str) -> dict:
    """Get Sentry issue details."""
    ...

@mcp.tool()
async def list_issues(project: str, status: str = "unresolved") -> list[dict]:
    """List Sentry issues for project."""
    ...

@mcp.tool()
async def resolve_issue(issue_id: str) -> dict:
    """Mark Sentry issue as resolved."""
    ...
```

## Environment Variables

Each MCP server needs:

```bash
# GitHub MCP
GITHUB_API_URL=http://github-api:3001

# Jira MCP
JIRA_API_URL=http://jira-api:3002

# Slack MCP
SLACK_API_URL=http://slack-api:3003

# Sentry MCP
SENTRY_API_URL=http://sentry-api:3004
```

## Docker Compose

```yaml
# docker-compose.mcp.yml
services:
  github-mcp:
    build: ./github-mcp
    ports:
      - "9001:9001"
    environment:
      - GITHUB_API_URL=http://github-api:3001

  jira-mcp:
    build: ./jira-mcp
    ports:
      - "9002:9002"
    environment:
      - JIRA_API_URL=http://jira-api:3002

  slack-mcp:
    build: ./slack-mcp
    ports:
      - "9003:9003"
    environment:
      - SLACK_API_URL=http://slack-api:3003

  sentry-mcp:
    build: ./sentry-mcp
    ports:
      - "9004:9004"
    environment:
      - SENTRY_API_URL=http://sentry-api:3004
```

## Health Checks

```bash
curl http://localhost:9001/health  # GitHub
curl http://localhost:9002/health  # Jira
curl http://localhost:9003/health  # Slack
curl http://localhost:9004/health  # Sentry
```

## Testing

```bash
cd mcp-servers/jira-mcp && pytest
cd mcp-servers/slack-mcp && pytest
cd mcp-servers/sentry-mcp && pytest
```
