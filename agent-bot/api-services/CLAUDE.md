# API Services

## Containers

| Service    | Port | Purpose                 |
| ---------- | ---- | ----------------------- |
| GitHub API | 3001 | GitHub REST API wrapper |
| Jira API   | 3002 | Jira REST API wrapper   |
| Slack API  | 3003 | Slack Web API wrapper   |
| Sentry API | 3004 | Sentry API wrapper      |

## Security Model

**IMPORTANT**: API keys are ONLY stored in API service containers. MCP servers and agent engines have NO access to API keys.

## Environment Variables

```bash
# GitHub API
GITHUB_TOKEN=ghp_xxx

# Jira API
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
JIRA_API_TOKEN=xxx

# Slack API
SLACK_BOT_TOKEN=xoxb-xxx

# Sentry API
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx
```

## Health Checks

```bash
curl http://localhost:3001/health  # GitHub
curl http://localhost:3002/health  # Jira
curl http://localhost:3003/health  # Slack
curl http://localhost:3004/health  # Sentry
```

## Error Handling

All services return standardized error responses:

```json
{
  "error": "not_found",
  "message": "Issue PROJ-999 not found",
  "status_code": 404
}
```

## Testing

```bash
cd api-services/github-api && pytest
cd api-services/jira-api && pytest
cd api-services/slack-api && pytest
cd api-services/sentry-api && pytest
```
