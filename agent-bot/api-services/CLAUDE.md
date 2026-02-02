# API Services

REST API wrappers for external services. Each service isolates API credentials and provides a standardized interface.

## Services

| Service    | Port | Purpose                       |
| ---------- | ---- | ----------------------------- |
| github-api | 3001 | GitHub API operations         |
| jira-api   | 3002 | Jira API operations           |
| slack-api  | 3003 | Slack API operations          |
| sentry-api | 3004 | Sentry API operations         |

## Security Model

**IMPORTANT**: API keys are ONLY stored in API service containers. MCP servers and agent engines have NO access to API keys.

## Folder Structure

Each service follows the same pattern:

```
api-services/{service}-api/
├── main.py              # FastAPI app entry point
├── api/                 # Routes and server
├── client/              # Service-specific client
├── middleware/          # Auth and error handling
├── config/              # Settings
└── tests/               # Co-located tests (self-contained)
    └── test_*.py        # Test files
```

## Testing

Tests are co-located and self-contained within each service.

```bash
# From agent-bot root - run all api-services tests
make test-services

# Or run individually
uv run pytest api-services/github-api/tests/ -v
uv run pytest api-services/jira-api/tests/ -v
uv run pytest api-services/slack-api/tests/ -v
uv run pytest api-services/sentry-api/tests/ -v
```

## Environment Variables

### GitHub API (3001)
```bash
GITHUB_TOKEN=ghp_xxx
PORT=3001
```

### Jira API (3002)
```bash
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=xxx
PORT=3002
```

### Slack API (3003)
```bash
SLACK_BOT_TOKEN=xoxb-xxx
PORT=3003
```

### Sentry API (3004)
```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx
PORT=3004
```

## Health Checks

```bash
curl http://localhost:3001/health  # GitHub
curl http://localhost:3002/health  # Jira
curl http://localhost:3003/health  # Slack
curl http://localhost:3004/health  # Sentry
```

## Development Rules

- Maximum 300 lines per file
- NO `any` types - use strict Pydantic models
- NO comments - self-explanatory code only
- Tests must run fast (< 5 seconds), no real network calls
- Use async/await for all I/O operations
- Use `httpx.AsyncClient` for HTTP requests
