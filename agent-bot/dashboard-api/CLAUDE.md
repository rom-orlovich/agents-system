# Dashboard API

Backend API for agent-bot dashboard (port 5000). Provides REST endpoints, WebSocket hub for real-time updates, analytics, and conversation management.

## API Endpoints

- `/api/tasks` - Task listing and details
- `/api/analytics/*` - Cost tracking, performance metrics
- `/api/conversations` - Chat interface management
- `/api/webhooks` - Webhook status monitoring
- `/ws` - WebSocket for real-time updates
- `/api/health` - Health check

## Core Responsibilities

1. **Task Management**: List, filter, retrieve task details
2. **Real-Time Streaming**: WebSocket streaming of task outputs
3. **Analytics**: Cost tracking, performance metrics, histograms
4. **Conversations**: Chat interface for agent interactions
5. **Webhook Status**: Monitor webhook configurations and events

## Folder Structure

```
dashboard-api/
├── main.py              # FastAPI application
├── api/                 # REST endpoints
├── core/                # Database, WebSocket hub
├── shared/              # Shared models
└── tests/               # Co-located tests
    ├── factories/       # All test factories
    ├── conftest.py      # Shared fixtures
    └── test_*.py        # Test files
```

## Testing

Tests are co-located with the service for portability.

```bash
# From agent-bot root
make test-dashboard

# Or directly
cd agent-bot
PYTHONPATH=dashboard-api:$PYTHONPATH uv run pytest dashboard-api/tests/ -v
```

### Test Factories

Import factories from `tests/factories/`:

```python
from .factories import TaskFactory, SessionFactory, TaskStatus
from .factories import ConversationFactory, WebhookFactory
from .factories.webhook_factory import WebhookValidationError
```

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0
AGENT_ENGINE_URL=http://agent-engine:8080
CORS_ORIGINS=http://localhost:3005,http://localhost:3002
PORT=5000
```

## WebSocket Protocol

**Subscribe**: `{"type": "subscribe", "channel": "task:{task_id}"}`

**Task Output**: `{"type": "task_output", "task_id": "...", "output": "..."}`

**Task Status**: `{"type": "task_status", "task_id": "...", "status": "completed"}`

## Development Rules

- Maximum 300 lines per file
- NO `any` types - use strict Pydantic models
- NO comments - self-explanatory code only
- Tests must run fast (< 5 seconds), no real network calls
- Use async/await for all I/O operations
