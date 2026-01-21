# Claude Code Agent

A self-managing machine where FastAPI runs as a daemon and Claude Code CLI is spawned on-demand per request.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CONTAINER (Pod)                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────────────────────────────────────────────┐    │
│   │         FastAPI Server (DAEMON - always running)     │    │
│   │   • Webhooks  • Dashboard API  • WebSocket          │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Task Queue (Redis)                      │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Worker (Python async)                   │    │
│   │   • Processes queue  • Spawns Claude CLI            │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│   ┌─────────────────────────────────────────────────────┐    │
│   │     Claude Code CLI (ON-DEMAND - spawn per task)    │    │
│   │   • Brain: /app/                                     │    │
│   │   • Planning: /app/agents/planning/                 │    │
│   │   • Executor: /app/agents/executor/                 │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Features

- 🧠 **Brain Orchestrator**: Main Claude CLI instance that manages sub-agents
- 🔄 **Dynamic Sub-Agents**: Planning and Executor agents spawned on-demand
- 📡 **Webhook Integration**: GitHub, Jira, Sentry webhook support
- 💬 **Conversational Dashboard**: Real-time WebSocket-based UI
- 📊 **Cost Tracking**: Per-task and per-session cost monitoring
- 🗄️ **Dual Storage**: Redis (queue/cache) + SQLite (persistence)
- 🔌 **Extensible**: Create webhooks, agents, and skills dynamically

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd claude-code-agent
```

2. Initialize the project:
```bash
make init
```

3. Edit `.env` with your configuration

4. Start the services:
```bash
make up
```

5. Access the dashboard:
```
http://localhost:8000
```

## Development

### Using `uv` (Recommended)

```bash
# Install dependencies
uv sync

# Run locally (without Docker)
make run-local

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

### Using Docker

```bash
# Build containers
make build

# Start services
make up

# View logs
make logs

# Stop services
make down

# Restart services
make restart
```

## Project Structure

```
claude-code-agent/
├── .claude/                    # Brain CLAUDE.md
├── agents/                     # Sub-agents
│   ├── planning/               # Planning agent
│   │   ├── .claude/CLAUDE.md
│   │   └── skills/
│   └── executor/               # Executor agent
│       ├── .claude/CLAUDE.md
│       └── skills/
├── api/                        # FastAPI routes
│   ├── dashboard.py            # Dashboard API
│   ├── websocket.py            # WebSocket endpoint
│   └── webhooks.py             # Webhook handlers
├── core/                       # Core logic
│   ├── config.py               # Configuration
│   ├── cli_runner.py           # Claude CLI executor
│   ├── background_manager.py   # Task manager
│   ├── websocket_hub.py        # WebSocket manager
│   ├── registry.py             # Registry pattern
│   └── database/               # Database layer
├── shared/                     # Shared models
│   └── machine_models.py       # Pydantic models
├── workers/                    # Background workers
│   └── task_worker.py          # Task processor
├── services/                   # Services
│   └── dashboard/              # Dashboard frontend
│       └── static/             # HTML/CSS/JS
├── skills/                     # Brain skills
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── data/                       # Persistent data
│   ├── db/                     # SQLite database
│   ├── config/                 # Configurations
│   ├── credentials/            # Auth credentials
│   └── registry/               # Entity registry
├── main.py                     # Application entry
├── pyproject.toml              # Dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Multi-container setup
└── Makefile                    # Convenience commands
```

## Core Components

### 1. Brain (Main Orchestrator)

The Brain is the main Claude CLI instance that:
- Manages sub-agents
- Handles simple queries directly
- Routes complex tasks to specialized agents
- Manages system configuration

**Location**: `/app/.claude/CLAUDE.md`

### 2. Sub-Agents

#### Planning Agent
- Analyzes bugs and issues
- Creates fix plans (PLAN.md)
- Does NOT implement code
- **Location**: `/app/agents/planning/`

#### Executor Agent
- Implements code changes
- Runs tests and builds
- Creates pull requests
- **Location**: `/app/agents/executor/`

### 3. Task Worker

Processes tasks from Redis queue:
1. Pops task from queue
2. Spawns Claude CLI from appropriate directory
3. Streams output to WebSocket
4. Saves results to database

### 4. Dashboard

Real-time web interface:
- Chat with Brain
- Monitor active tasks
- View costs and metrics
- Manage agents and webhooks

**Access**: `http://localhost:8000`

### 5. Webhooks

Handle external events:
- **GitHub**: `/webhooks/github` - Issues, PRs, comments
- **Jira**: `/webhooks/jira` - Ticket updates
- **Sentry**: `/webhooks/sentry` - Error alerts

## API Endpoints

### Dashboard API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Machine status |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task details |
| POST | `/api/tasks/{id}/stop` | Stop task |
| POST | `/api/chat` | Send message to Brain |
| GET | `/api/agents` | List agents |
| GET | `/api/webhooks` | List webhooks |

### WebSocket

- **Endpoint**: `/ws/{session_id}`
- **Events**: task.created, task.output, task.completed, task.failed

### Webhooks

| Endpoint | Description |
|----------|-------------|
| `/webhooks/github` | GitHub events |
| `/webhooks/jira` | Jira events |
| `/webhooks/sentry` | Sentry events |

## Configuration

### Environment Variables

```bash
# Machine
MACHINE_ID=claude-agent-001
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600

# Database
REDIS_URL=redis://redis:6379/0
DATABASE_URL=sqlite+aiosqlite:////data/db/machine.db

# Logging
LOG_LEVEL=INFO
LOG_JSON=true
```

### Pydantic Settings

All configuration uses Pydantic with validation:
- Type-safe settings
- Environment variable support
- Automatic validation

## Testing

### Run All Tests

```bash
make test
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v -m integration

# With coverage
make test-cov
```

### Test Structure

- **Unit tests**: Pydantic models, business logic
- **Integration tests**: API endpoints, database
- **E2E tests**: Full workflows (planned)

## Database

### Redis (Ephemeral)

Used for:
- Task queue
- Current task status
- Live output buffering
- Session tracking

### SQLite (Persistent)

Used for:
- Session history
- Completed tasks
- Cost tracking
- Entity registry

### Accessing Databases

```bash
# SQLite
make db-shell

# Redis
make redis-cli
```

## Logging

Structured logging with `structlog`:

```json
{
  "timestamp": "2026-01-21T20:00:00Z",
  "level": "info",
  "event": "Task started",
  "task_id": "task-abc123",
  "agent": "planning"
}
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/health
```

### Metrics

- Active tasks
- Queue length
- Session count
- Total costs

## Troubleshooting

### Tasks Not Processing

1. Check worker is running:
```bash
docker-compose ps
```

2. Check Redis queue:
```bash
make redis-cli
> LLEN task_queue
```

3. Check logs:
```bash
make logs
```

### Database Issues

1. Check database file exists:
```bash
docker-compose exec app ls -la /data/db/
```

2. Open database shell:
```bash
make db-shell
> .tables
> SELECT * FROM tasks LIMIT 5;
```

### WebSocket Connection Issues

1. Check firewall settings
2. Verify CORS configuration
3. Check browser console for errors

## Production Deployment

### Kubernetes

See `k8s/` directory for manifests (coming soon).

### Docker Swarm

```bash
docker stack deploy -c docker-compose.yml claude-agent
```

### Environment Checklist

- [ ] Set unique MACHINE_ID
- [ ] Configure CORS_ORIGINS
- [ ] Set appropriate MAX_CONCURRENT_TASKS
- [ ] Enable health checks
- [ ] Configure log aggregation
- [ ] Set up monitoring
- [ ] Configure backups for /data volume

## Architecture Principles

1. **Pydantic Everywhere**: All domain logic enforced via Pydantic models
2. **On-Demand CLI**: Claude CLI spawned per request, not always running
3. **Type Safety**: Full typing with mypy strict mode
4. **Asyncio Native**: All I/O operations are async
5. **TDD**: Tests for business logic first

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [link]
- Documentation: [link]
- Discord: [link]

---

**Built with ❤️ using Claude Code CLI**
