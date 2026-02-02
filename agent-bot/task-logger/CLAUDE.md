# Task Logger

Dedicated service for structured task logging (port 8090). Consumes task events from Redis stream and writes structured log files.

## API Endpoints

- `GET /health` - Health check
- `GET /tasks/{task_id}/logs` - Retrieve task logs
- `GET /metrics` - Queue depth, processed count

## Event Types

**Webhook Events**: `webhook:received`, `webhook:validated`, `webhook:matched`, `webhook:task_created`

**Task Events**: `task:created`, `task:started`, `task:output`, `task:user_input`, `task:completed`, `task:failed`

## Log Structure

```
/data/logs/tasks/{task_id}/
├── metadata.json          # Task metadata
├── 01-input.json          # Initial task input
├── 02-webhook-flow.jsonl  # Webhook processing events
├── 03-agent-output.jsonl  # Claude output, thinking, tool calls
├── 03-user-inputs.jsonl   # User interactive inputs
└── 04-final-result.json   # Final results + metrics
```

## Folder Structure

```
task-logger/
├── main.py              # FastAPI app + Redis consumer
├── worker.py            # Event processing worker
├── logger.py            # File logging utilities
├── models.py            # Pydantic models
├── config.py            # Settings
└── tests/               # Co-located tests (self-contained)
    ├── conftest.py      # Shared fixtures
    └── test_*.py        # Test files
```

## Testing

Tests are co-located and self-contained (no shared dependencies).

```bash
# From agent-bot root
make test-logger

# Or directly
cd agent-bot
PYTHONPATH=task-logger:$PYTHONPATH uv run pytest task-logger/tests/ -v
```

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
LOGS_DIR=/data/logs/tasks
REDIS_STREAM=task_events
REDIS_CONSUMER_GROUP=task-logger
MAX_BATCH_SIZE=10
PORT=8090
```

## Development Rules

- Maximum 300 lines per file
- NO `any` types - use strict Pydantic models
- NO comments - self-explanatory code only
- Tests must run fast (< 5 seconds), no real network calls
- Use async/await for all I/O operations
- Atomic writes (temp file + rename) for reliability
