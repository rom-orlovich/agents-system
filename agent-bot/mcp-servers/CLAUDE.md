# MCP Servers

MCP servers (ports 9001-9004) connect to agent engine via SSE. They call API services (ports 3001-3004) for actual API operations.

## Services

- GitHub MCP (9001) - Official Node.js
- Jira MCP (9002) - Custom FastMCP (Python)
- Slack MCP (9003) - Custom FastMCP (Python)
- Sentry MCP (9004) - Custom FastMCP (Python)

## Environment Variables

Each MCP server needs: `{PROVIDER}_API_URL=http://{provider}-api:300{port}`

## Health Checks

```bash
curl http://localhost:9001/health  # GitHub
curl http://localhost:9002/health  # Jira
curl http://localhost:9003/health  # Slack
curl http://localhost:9004/health  # Sentry
```
