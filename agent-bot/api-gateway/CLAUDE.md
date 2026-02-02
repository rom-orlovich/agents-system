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

## Folder Structure

```
api-gateway/
├── main.py              # FastAPI app entry point
├── routes/              # Route registration
├── webhooks/            # Webhook handlers (github/, jira/, slack/, sentry/)
├── middleware/          # Error handling
├── config/              # Settings
└── tests/               # Co-located tests
    ├── fixtures/        # Webhook payload fixtures
    ├── conftest.py      # Shared fixtures
    └── test_*.py        # Test files
```

## Testing

Tests are co-located with the service for portability.

```bash
# From agent-bot root
make test-api-gateway

# Or directly
cd agent-bot
PYTHONPATH=api-gateway:$PYTHONPATH uv run pytest api-gateway/tests/ -v
```

### Test Fixtures

Import fixtures from `tests/fixtures/`:

```python
from .fixtures import (
    github_issue_opened_payload,
    jira_issue_created_payload,
    slack_app_mention_payload,
    sentry_issue_created_payload,
)
```

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

## Development Rules

- Maximum 300 lines per file
- NO `any` types - use strict Pydantic models
- NO comments - self-explanatory code only
- Tests must run fast (< 5 seconds), no real network calls
- Use async/await for all I/O operations
