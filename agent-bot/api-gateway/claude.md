# API Gateway - Claude Code Configuration

## Component Overview

The API Gateway is the entry point for all webhook events from external services (GitHub, Jira, Slack, Sentry). It handles webhook validation, routing, task creation, and queue management.

## Architecture Role

- **Receives webhooks** from external providers
- **Validates signatures** using provider-specific validation
- **Routes webhooks** to dedicated handlers (GitHub, Jira, Slack, Sentry)
- **Creates tasks** and enqueues them for agent processing
- **Logs task lifecycle** using centralized TaskLogger
- **Provides metrics** via Prometheus

## Key Components

### Webhook Handlers (Separate Concern Pattern)
- `webhooks/github_handler.py` - GitHub webhook processing
- `webhooks/jira_handler.py` - Jira webhook processing
- `webhooks/slack_handler.py` - Slack webhook processing
- `webhooks/sentry_handler.py` - Sentry webhook processing

Each handler is INDEPENDENT with:
- Own signature validation
- Own payload parsing
- Own command extraction
- Own task creation logic

### Core Systems
- `core/task_logger.py` - Centralized task lifecycle logging
- `queue/redis_queue.py` - Priority-based task queue
- `storage/repositories.py` - Database access layer
- `core/circuit_breaker.py` - Fault tolerance
- `core/retry.py` - Exponential backoff retry logic

## Development Rules

### Strict Type Safety ✅
- NO `any` types allowed
- All Pydantic models use `ConfigDict(strict=True)`
- Explicit Optional handling

### Self-Explanatory Code ✅
- NO comments in code
- Clear, descriptive naming
- Well-structured organization

### TDD Approach ✅
- Write tests FIRST
- Test files in `tests/`
- Use fakeredis and aiosqlite for testing

### Modular Design ✅
- Separate handler per webhook provider (NO if/else chains)
- Protocol-based interfaces
- Dependency injection

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific handler tests
pytest tests/test_github_webhook_handler.py -v

# With coverage
pytest --cov=. --cov-report=html
```

## Available Skills

When working in this component, you have access to:
- `webhook-handling` - Process incoming webhooks
- `task-logging` - Log task lifecycle events
- `queue-management` - Enqueue/dequeue tasks
- `signature-validation` - Validate webhook signatures
- `circuit-breaking` - Handle service failures
- `retry-logic` - Retry failed operations

## Common Tasks

### Adding New Webhook Handler
1. Create test file: `tests/test_{provider}_webhook_handler.py`
2. Write tests for success, validation, error cases
3. Create handler: `webhooks/{provider}_handler.py`
4. Implement using same pattern as GitHub handler
5. Add route in `main.py`
6. Run tests: `pytest tests/test_{provider}_webhook_handler.py`

### Adding Database Model
1. Create test in `tests/test_repositories.py`
2. Add model in `storage/models.py`
3. Add repository method in `storage/repositories.py`
4. Create Alembic migration: `alembic revision -m "description"`
5. Run tests

## Environment Variables

```
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://...
TASK_LOGS_DIR=/data/logs/tasks
GITHUB_WEBHOOK_SECRET=secret
SLACK_SIGNING_SECRET=secret
JIRA_WEBHOOK_SECRET=secret
SENTRY_WEBHOOK_SECRET=secret
```

## Metrics Exposed

- `webhook_requests_total{provider, status}`
- `task_processing_duration_seconds`
- `tasks_in_queue`
- `webhook_signature_validation_failures_total{provider}`

## Related Components

- **Agent Container**: Consumes tasks from queue
- **MCP Servers**: Provide tools for task execution
- **Dashboard API**: Reads task logs and metrics
