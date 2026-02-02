# API Gateway

Central webhook reception (port 8000). Receives webhooks from GitHub, Jira, Slack, Sentry, validates signatures, and enqueues tasks to Redis.

## Webhook Endpoints

- `/webhooks/github` - GitHub events (PR, issues, comments)
- `/webhooks/jira` - Jira events (ticket assignment, status)
- `/webhooks/slack` - Slack events (mentions, commands)
- `/webhooks/sentry` - Sentry alerts
- `/health` - Health check

## Processing Flow

1. Verify signature (HMAC for GitHub/Slack)
2. Check loop prevention (skip bot messages via Redis: `posted_comments:{comment_id}`, TTL 3600s)
3. Create task in PostgreSQL
4. Queue task to Redis
5. Return 200 OK

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

## Testing

```bash
cd api-gateway && pytest
```
