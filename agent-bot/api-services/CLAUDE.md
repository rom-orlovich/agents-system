# API Services

REST API wrappers (ports 3001-3004): GitHub API (3001), Jira API (3002), Slack API (3003), Sentry API (3004).

## Security Model

**IMPORTANT**: API keys are ONLY stored in API service containers. MCP servers and agent engines have NO access to API keys.

## Environment Variables

- GitHub: `GITHUB_TOKEN=ghp_xxx`
- Jira: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- Slack: `SLACK_BOT_TOKEN=xoxb-xxx`
- Sentry: `SENTRY_DSN`, `SENTRY_AUTH_TOKEN`

## Health Checks

```bash
curl http://localhost:3001/health  # GitHub
curl http://localhost:3002/health  # Jira
curl http://localhost:3003/health  # Slack
curl http://localhost:3004/health  # Sentry
```
