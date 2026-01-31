# MCP Servers

## Containers

| Service    | Port | Type     | Framework        |
| ---------- | ---- | -------- | ---------------- |
| GitHub MCP | 9001 | Official | Node.js          |
| Jira MCP   | 9002 | Custom   | FastMCP (Python) |
| Slack MCP  | 9003 | Custom   | FastMCP (Python) |
| Sentry MCP | 9004 | Custom   | FastMCP (Python) |

## Architecture

MCP servers connect to agent engine via SSE (Server-Sent Events). They call API services (ports 3001-3004) for actual API operations.

## Environment Variables

Each MCP server needs:

```bash
GITHUB_API_URL=http://github-api:3001
JIRA_API_URL=http://jira-api:3002
SLACK_API_URL=http://slack-api:3003
SENTRY_API_URL=http://sentry-api:3004
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
