# Dashboard API Service

> Backend API for agent-bot dashboard with real-time task streaming, analytics, and conversation management.

## Purpose

The Dashboard API provides REST endpoints and WebSocket connections for the agent-bot dashboard. It handles task management, analytics, conversations, webhook status monitoring, and real-time updates.

## Architecture

```
Dashboard Frontend (React)
         │
         │ HTTP + WebSocket
         ▼
┌─────────────────────────────────────┐
│      Dashboard API :5000            │
│                                     │
│  1. REST API Endpoints             │
│     - /api/tasks                   │
│     - /api/analytics               │
│     - /api/conversations           │
│     - /api/webhooks                │
│                                     │
│  2. WebSocket Hub                  │
│     - /ws (real-time updates)      │
│                                     │
│  3. Data Sources                   │
│     - PostgreSQL (tasks, convos)   │
│     - Redis (task status, cache)   │
└─────────────────────────────────────┘
         │
         ▼
    PostgreSQL + Redis
```

## Folder Structure

```
dashboard-api/
├── main.py                    # FastAPI application
├── api/
│   ├── dashboard.py           # Dashboard endpoints
│   ├── analytics.py           # Analytics endpoints
│   ├── conversations.py       # Conversation endpoints
│   ├── webhook_status.py       # Webhook monitoring
│   └── websocket.py           # WebSocket handler
├── core/
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── redis_client.py    # Redis client
│   ├── websocket_hub.py       # WebSocket connection manager
│   └── webhook_configs.py     # Webhook configuration loader
├── shared/
│   └── machine_models.py      # Shared Pydantic models
└── tests/                     # Co-located tests
    ├── factories/             # Test data factories
    │   ├── task_factory.py    # Task model and factory
    │   ├── session_factory.py # Session model and factory
    │   ├── conversation_factory.py # Conversation factory
    │   └── webhook_factory.py # Webhook config factory
    ├── conftest.py            # Shared fixtures
    └── test_*.py              # Test files
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

Test factories are in `tests/factories/`:

```python
from .factories import TaskFactory, SessionFactory, TaskStatus
from .factories import ConversationFactory, WebhookFactory
from .factories.webhook_factory import WebhookValidationError
```

## Business Logic

### Core Responsibilities

1. **Task Management**: List, filter, retrieve task details
2. **Real-Time Streaming**: WebSocket streaming of task outputs
3. **Analytics**: Cost tracking, performance metrics, histograms
4. **Conversations**: Chat interface for agent interactions
5. **Webhook Status**: Monitor webhook configurations and events
6. **WebSocket Hub**: Manage WebSocket connections for live updates

## API Endpoints

### Dashboard

| Endpoint                         | Method | Purpose                    |
| -------------------------------- | ------ | -------------------------- |
| `/api/status`                    | GET    | Machine status             |
| `/api/tasks`                     | GET    | List tasks with pagination |
| `/api/tasks/{task_id}`           | GET    | Task details               |
| `/api/tasks/{task_id}/logs/full` | GET    | Complete task logs         |
| `/api/agents`                    | GET    | List available agents      |

### Analytics

| Endpoint                         | Method | Purpose                |
| -------------------------------- | ------ | ---------------------- |
| `/api/analytics/summary`         | GET    | Analytics summary      |
| `/api/analytics/costs/histogram` | GET    | Cost breakdown by time |
| `/api/analytics/performance`     | GET    | Performance metrics    |

### Conversations

| Endpoint                           | Method | Purpose             |
| ---------------------------------- | ------ | ------------------- |
| `/api/conversations`               | GET    | List conversations  |
| `/api/conversations`               | POST   | Create conversation |
| `/api/conversations/{id}/messages` | GET    | Get messages        |

### Webhooks

| Endpoint               | Method | Purpose                |
| ---------------------- | ------ | ---------------------- |
| `/api/webhooks`        | GET    | Webhook configurations |
| `/api/webhooks/events` | GET    | Webhook events         |
| `/api/webhooks/stats`  | GET    | Webhook statistics     |

### WebSocket

| Endpoint | Protocol  | Purpose           |
| -------- | --------- | ----------------- |
| `/ws`    | WebSocket | Real-time updates |

## WebSocket Protocol

**Subscribe to Task Updates**:

```json
{
  "type": "subscribe",
  "channel": "task:{task_id}"
}
```

**Task Output Stream**:

```json
{
  "type": "task_output",
  "task_id": "uuid",
  "output": "CLI output line",
  "timestamp": "2026-01-31T12:00:00Z"
}
```

**Task Status Update**:

```json
{
  "type": "task_status",
  "task_id": "uuid",
  "status": "completed",
  "result": {
    "stdout": "...",
    "cost_usd": 0.05,
    "input_tokens": 1000,
    "output_tokens": 500
  }
}
```

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0
AGENT_ENGINE_URL=http://agent-engine:8080
CORS_ORIGINS=http://localhost:3005,http://localhost:3002
PORT=5000
LOG_LEVEL=INFO
```

## Analytics

**Cost Tracking**:

- Input/output tokens per task
- Cost in USD
- Model used
- Agent type

**Performance Metrics**:

- Task duration
- Success rate
- Average tokens per task
- Cost per task

**Histograms**:

- Costs per hour/day
- Task counts per hour/day
- Token usage per hour/day

## Health Check

```bash
curl http://localhost:5000/api/health
```

## Related Services

- **external-dashboard**: React frontend that consumes this API
- **agent-engine**: Publishes task updates to Redis/WebSocket
- **api-gateway**: Creates tasks that appear in dashboard
