# API Gateway Container

> Central webhook reception and routing service.

## Purpose

The API Gateway receives webhooks from external services (GitHub, Jira, Slack, Sentry), validates signatures, extracts routing metadata, and enqueues tasks to Redis.

## Container Details

| Property | Value |
|----------|-------|
| Port | 8000 |
| Scalable | No (single instance) |
| Base Image | python:3.11-slim |
| Framework | FastAPI |

## Architecture

```
GitHub/Jira/Slack/Sentry
         │
         ▼
┌─────────────────────────────┐
│      API Gateway :8000      │
│  ┌───────────────────────┐ │
│  │  Webhook Handlers     │ │
│  │  ├── /webhooks/github │ │
│  │  ├── /webhooks/jira   │ │
│  │  ├── /webhooks/slack  │ │
│  │  └── /webhooks/sentry │ │
│  └───────────────────────┘ │
│            │                │
│            ▼                │
│  ┌───────────────────────┐ │
│  │  Validation           │ │
│  │  - Signature (HMAC)   │ │
│  │  - Payload schema     │ │
│  │  - Loop prevention    │ │
│  └───────────────────────┘ │
│            │                │
│            ▼                │
│  ┌───────────────────────┐ │
│  │  Task Creation        │ │
│  │  - Extract metadata   │ │
│  │  - Create task in DB  │ │
│  │  - Queue to Redis     │ │
│  └───────────────────────┘ │
└─────────────────────────────┘
         │
         ▼
    Redis Queue
```

## Key Files

```
api-gateway/
├── Dockerfile
├── CLAUDE.md               # This file
├── main.py                 # FastAPI entry point
├── requirements.txt
└── webhooks/
    ├── __init__.py
    ├── github/
    │   ├── handler.py      # GitHub webhook processing
    │   ├── validator.py    # Signature validation
    │   ├── events.py       # Event type handling
    │   └── models.py       # Pydantic models
    ├── jira/
    │   ├── handler.py
    │   ├── validator.py
    │   ├── events.py
    │   └── models.py
    ├── slack/
    │   ├── handler.py
    │   ├── validator.py
    │   ├── events.py
    │   └── models.py
    └── sentry/
        ├── handler.py
        ├── validator.py
        ├── events.py
        └── models.py
```

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

## Webhook Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhooks/github` | POST | GitHub events (PR, issues, comments) |
| `/webhooks/jira` | POST | Jira events (ticket assignment, status) |
| `/webhooks/slack` | POST | Slack events (mentions, commands) |
| `/webhooks/sentry` | POST | Sentry alerts |
| `/health` | GET | Health check |

## Webhook Processing Flow

### GitHub

1. Receive POST to `/webhooks/github`
2. Verify `X-Hub-Signature-256` header
3. Parse `X-GitHub-Event` header
4. Extract routing metadata (owner, repo, PR/issue number)
5. Check for `@agent` command in comment body
6. Skip if from bot username
7. Create task and queue to Redis
8. Return 200 OK

### Jira

1. Receive POST to `/webhooks/jira`
2. Verify signature (if configured)
3. Parse issue data from payload
4. Check assignee matches AI agent
5. Create task and queue to Redis
6. Return 200 OK

### Slack

1. Receive POST to `/webhooks/slack`
2. Verify `X-Slack-Signature` header
3. Handle URL verification challenge
4. Parse event (mention, command)
5. Skip if from bot user
6. Create task and queue to Redis
7. Return 200 OK

## Loop Prevention

Bot comments/messages are tracked in Redis to prevent infinite loops:

```python
redis_key = f"posted_comments:{comment_id}"
ttl = 3600  # 1 hour
```

## Error Handling

- 401: Invalid signature
- 400: Invalid payload
- 500: Internal error

All errors logged with structured logging.

## Health Check

```bash
curl http://localhost:8000/health
```

## Testing

```bash
cd api-gateway
pytest
```
