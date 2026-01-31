# Internal Dashboard API

> Agent management and monitoring API service.

## Purpose

The Internal Dashboard API provides endpoints for managing agents, monitoring tasks, and collecting metrics. It serves as the backend for the External Dashboard.

## Container Details

| Property | Value |
|----------|-------|
| Port | 5000 |
| Scalable | No (single instance) |
| Base Image | python:3.11-slim |
| Framework | FastAPI |

## Architecture

```
External Dashboard (React)
         │
         │ HTTP / WebSocket
         ▼
┌─────────────────────────────────────┐
│   Internal Dashboard API :5000      │
│  ┌───────────────────────────────┐ │
│  │  REST Endpoints               │ │
│  │  ├── /api/tasks               │ │
│  │  ├── /api/agents              │ │
│  │  ├── /api/metrics             │ │
│  │  └── /api/conversations       │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  WebSocket Hub                │ │
│  │  - Real-time task updates     │ │
│  │  - Log streaming              │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │     Redis       │
│     :5432       │ │     :6379       │
└─────────────────┘ └─────────────────┘
```

## Key Files

```
internal-dashboard-api/
├── Dockerfile
├── CLAUDE.md               # This file
├── main.py                 # FastAPI entry point
├── requirements.txt
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── tasks.py        # Task endpoints
│       ├── agents.py       # Agent endpoints
│       ├── metrics.py      # Metrics endpoints
│       └── conversations.py
└── services/
    ├── task_manager.py
    ├── agent_manager.py
    └── metrics_collector.py
```

## API Endpoints

### Tasks

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tasks` | GET | List tasks (with filters) |
| `/api/tasks/{id}` | GET | Get task details |
| `/api/tasks/{id}/logs` | GET | Get task logs |
| `/api/tasks/{id}/cancel` | POST | Cancel running task |

### Agents

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents` | GET | List all agents |
| `/api/agents/{name}` | GET | Get agent details |
| `/api/agents/{name}/status` | GET | Get agent status |

### Metrics

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/metrics` | GET | Get aggregated metrics |
| `/api/metrics/tasks` | GET | Task metrics |
| `/api/metrics/costs` | GET | Cost metrics |
| `/api/metrics/prometheus` | GET | Prometheus format |

### Conversations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/conversations` | GET | List conversations |
| `/api/conversations/{id}` | GET | Get conversation with messages |
| `/api/conversations/{id}/messages` | POST | Add message |

## WebSocket

Connect to `/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'task_update':
      // Handle task status change
      break;
    case 'task_output':
      // Handle streaming output
      break;
    case 'metrics_update':
      // Handle metrics update
      break;
  }
};
```

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0
AGENT_ENGINE_URL=http://agent-engine:8080
```

## Metrics

Prometheus metrics available at `/api/metrics/prometheus`:

```
# HELP agent_tasks_total Total number of tasks processed
# TYPE agent_tasks_total counter
agent_tasks_total{status="completed"} 150
agent_tasks_total{status="failed"} 10

# HELP agent_task_duration_seconds Task duration in seconds
# TYPE agent_task_duration_seconds histogram
agent_task_duration_seconds_bucket{le="60"} 50
agent_task_duration_seconds_bucket{le="300"} 120

# HELP agent_cost_usd_total Total cost in USD
# TYPE agent_cost_usd_total counter
agent_cost_usd_total 45.67
```

## Health Check

```bash
curl http://localhost:5000/health
```

## Testing

```bash
cd internal-dashboard-api
pytest
```
