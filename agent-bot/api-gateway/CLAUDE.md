# API Gateway

## Purpose

Central webhook reception and routing service. Receives webhooks from GitHub, Jira, Slack, Sentry, validates signatures, extracts routing metadata, and enqueues tasks to Redis.

## Container Details

| Property  | Value                |
| --------- | -------------------- |
| Port      | 8000                 |
| Scalable  | No (single instance) |
| Framework | FastAPI              |

## Webhook Endpoints

| Endpoint           | Method | Purpose                                 |
| ------------------ | ------ | --------------------------------------- |
| `/webhooks/github` | POST   | GitHub events (PR, issues, comments)    |
| `/webhooks/jira`   | POST   | Jira events (ticket assignment, status) |
| `/webhooks/slack`  | POST   | Slack events (mentions, commands)       |
| `/webhooks/sentry` | POST   | Sentry alerts                           |
| `/health`          | GET    | Health check                            |

## Webhook Processing Flow

1. Receive POST to `/webhooks/{provider}`
2. Verify signature (HMAC for GitHub/Slack, configurable for Jira)
3. Parse event data and extract routing metadata
4. Check for loop prevention (skip bot messages)
5. Create task in PostgreSQL
6. Queue task to Redis
7. Return 200 OK

## Loop Prevention

Bot comments/messages tracked in Redis to prevent infinite loops:

```python
redis_key = f"posted_comments:{comment_id}"
ttl = 3600  # 1 hour
```

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

## Error Handling

- 401: Invalid signature
- 400: Invalid payload
- 500: Internal error

All errors logged with structured logging.

## Testing

```bash
cd api-gateway
pytest
```
