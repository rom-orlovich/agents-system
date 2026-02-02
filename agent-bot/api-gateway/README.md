# API Gateway Service

> Central webhook reception and routing service for agent-bot system.

## Purpose

The API Gateway receives webhooks from GitHub, Jira, Slack, and Sentry, validates signatures, extracts routing metadata, and enqueues tasks to Redis for processing by agent-engine.

## Architecture

```
External Service (GitHub/Jira/Slack/Sentry)
         │
         ▼
┌─────────────────────────────────────┐
│      API Gateway :8000              │
│                                     │
│  [Middleware Layer]                │
│  1. Receive POST request           │
│  2. Validate HMAC signature        │
│     ┌───────────────────────────┐ │
│     │ IF INVALID:                │ │
│     │ → Return 401 immediately  │ │
│     └───────────────────────────┘ │
│                                     │
│  [Handler Layer]                   │
│  3. Parse event payload            │
│  4. Extract routing metadata       │
│  5. Check if event should process   │
│     ┌───────────────────────────┐ │
│     │ IF SKIPPED:                │ │
│     │ → Return 200 OK            │ │
│     │   {"status": "skipped"}    │ │
│     └───────────────────────────┘ │
│              │                     │
│              │ (if accepted)      │
│              ▼                     │
│  6. Create task metadata           │
│  7. Generate task_id                │
│  8. Enqueue to Redis               │
│     ┌───────────────────────────┐ │
│     │ IF ACCEPTED:              │ │
│     │ → Return 202 Accepted    │ │
│     │   {"status": "accepted",  │ │
│     │    "task_id": "uuid"}     │ │
│     └───────────────────────────┘ │
└─────────────────────────────────────┘
         │ ✅ Response < 50ms
         │ ⏳ Task processing async
         ▼
    Redis Queue → Agent Engine
```

## Folder Structure

```
api-gateway/
├── main.py                    # FastAPI app entry point
├── routes/
│   └── webhooks.py           # Webhook route registration
├── webhooks/
│   ├── github/               # GitHub webhook handler
│   │   ├── handler.py        # Event processing
│   │   ├── validator.py      # HMAC validation + middleware
│   │   ├── events.py         # Event type routing
│   │   └── models.py         # Pydantic models
│   ├── jira/                 # Jira webhook handler
│   ├── slack/                # Slack webhook handler
│   └── sentry/               # Sentry webhook handler
├── middleware/
│   └── error_handler.py      # WebhookValidationError class
├── config/
│   └── settings.py           # Configuration
└── tests/                     # Co-located tests
    ├── fixtures/              # Webhook payload fixtures
    │   ├── github_payloads.py
    │   ├── jira_payloads.py
    │   ├── slack_payloads.py
    │   └── sentry_payloads.py
    ├── conftest.py            # Shared fixtures
    └── test_*.py              # Test files
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

Webhook payload fixtures are in `tests/fixtures/`:

```python
from .fixtures import (
    github_issue_opened_payload,
    jira_issue_created_payload,
    slack_app_mention_payload,
    sentry_issue_created_payload,
)
```

## Business Logic

### Core Responsibilities

1. **Webhook Reception**: HTTP POST from external services
2. **Security Validation**: HMAC signature verification (middleware)
3. **Event Parsing**: Extract metadata (repo, PR, ticket key)
4. **Task Creation**: Generate task_id, create task metadata
5. **Queue Management**: Enqueue to Redis for agent-engine
6. **Immediate Response**: Return 202/200 within 50ms

### Response Types

**1. Immediate HTTP Response** (< 50ms):

- `202 Accepted`: Event queued → `{"status": "accepted", "task_id": "uuid"}`
- `200 OK`: Event skipped → `{"status": "skipped"}`
- `401 Unauthorized`: Invalid signature (middleware)

**2. Immediate Visual Response** (async, < 100ms):

- GitHub: 👀 reaction on comment OR acknowledgment comment
- Via `github-api` service

**3. Final Result** (after task completion):

- Success: ✅ comment with results + cost
- Failure: 👎 reaction on original comment (no new comment)

## API Endpoints

| Endpoint           | Method | Response                   |
| ------------------ | ------ | -------------------------- |
| `/webhooks/github` | POST   | `202 Accepted` or `200 OK` |
| `/webhooks/jira`   | POST   | `202 Accepted` or `200 OK` |
| `/webhooks/slack`  | POST   | `200 OK` (all responses)   |
| `/webhooks/sentry` | POST   | `202 Accepted` or `200 OK` |
| `/health`          | GET    | `200 OK`                   |

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
SENTRY_WEBHOOK_SECRET=xxx
```

## Webhook Processing

### GitHub Flow

1. Receive POST → Validate signature (middleware)
2. Parse `X-GitHub-Event` header
3. Extract metadata (owner, repo, PR/issue number)
4. Check `@agent` command in comment
5. Skip if from bot → Return `200 OK`
6. Create task → Queue to Redis → Return `202 Accepted`
7. Async: Add 👀 reaction via `github-api`

### Jira Flow

1. Receive POST → Validate signature (middleware)
2. Parse issue data
3. Check AI-Fix label → Skip if missing → Return `200 OK`
4. Check assignee matches AI agent
5. Create task → Queue to Redis → Return `202 Accepted`

### Slack Flow

1. Receive POST → Handle URL verification challenge
2. Validate signature (middleware)
3. Parse event (mention, command)
4. Skip if from bot → Return `200 OK`
5. Create task → Queue to Redis → Return `200 OK`

### Sentry Flow

1. Receive POST → Validate signature (middleware)
2. Parse alert data
3. Skip if unsupported → Return `200 OK`
4. Create task → Queue to Redis → Return `202 Accepted`

## Error Handling

**Middleware-based** (no separate error handler):

- **401**: Invalid signature → `GitHubAuthMiddleware` returns 401 JSONResponse
- **400**: Invalid payload → Handler returns 400
- **500**: Queue error → Handler returns 500

All errors logged with structured logging.

## Task Structure

```python
{
    "task_id": "uuid",
    "source": "github" | "jira" | "slack" | "sentry",
    "event_type": "issue_comment" | "pull_request" | ...,
    "prompt": "User's request text",
    "source_metadata": {
        # GitHub: owner, repo, pr_number, issue_number, comment_id
        # Jira: ticket_key, project
        # Slack: channel_id, thread_ts, user_id
    },
    "agent_type": "github-issue-handler" | "jira-code-plan" | ...,
    "repo_path": "/app/repos/{owner}/{repo}",
    "status": "pending"
}
```

## Loop Prevention

- Redis tracking of posted comment IDs (TTL: 1 hour)
- Bot username detection
- Skip events from known bot accounts

## Health Check

```bash
curl http://localhost:8000/health
```

## Related Services

- **agent-engine**: Consumes tasks from Redis queue
- **github-api**: Posts visual responses (👀 reactions, comments)
- **dashboard-api**: Receives task status updates
