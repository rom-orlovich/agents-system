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
│   │   • Agents: .claude/agents/*.md                      │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Features

- 🧠 **Brain Orchestrator**: Main Claude CLI instance that manages sub-agents
- 💬 **Persistent Conversations**: Inbox-style UI with context awareness
- 📡 **Unified Webhooks**: Fully configurable GitHub, Jira, Slack, Sentry integration
- 🔄 **Specialized Agents**: Planning, Executor, Service Integrator, Self-Improvement, Agent Creator, Skill Creator
- 📊 **Cost Tracking**: Per-task and per-session cost monitoring
- 🗄️ **Dual Storage**: Redis (queue/cache) + SQLite (persistence)
- 🔌 **Extensible**: Create webhooks, agents, and skills dynamically
- 🧪 **TDD Workflow**: Full test-driven development with E2E validation
- 🔗 **Service Integration**: Cross-service workflows (GitHub, Jira, Slack, Sentry)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- `uv` package manager (recommended for local development)

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
├── .claude/                    # Brain instructions
│   ├── CLAUDE.md              # Main brain configuration
│   ├── agents/                 # Agent definitions (.md)
│   │   ├── brain.md           # Main orchestrator
│   │   ├── planning.md         # Analysis agent
│   │   ├── executor.md         # Implementation agent
│   │   ├── service-integrator.md # Service integration agent
│   │   ├── self-improvement.md  # Code improvement agent
│   │   ├── agent-creator.md    # Agent creation agent
│   │   └── skill-creator.md    # Skill creation agent
│   └── skills/                 # Reusable skills
│       ├── webhook-management/ # Webhook operations
│       ├── testing/            # TDD workflow
│       ├── github-operations/  # GitHub integration
│       ├── jira-operations/    # Jira integration
│       ├── slack-operations/   # Slack integration
│       ├── sentry-operations/  # Sentry integration
│       └── ...                 # Other skills
├── api/                        # FastAPI routes
│   ├── dashboard.py            # Dashboard API
│   ├── conversations.py        # Conversation management
│   ├── websocket.py            # WebSocket endpoint
│   ├── webhooks.py             # Webhook handlers
│   └── ...                     # Other API endpoints
├── core/                       # Core logic
│   ├── config.py               # Configuration
│   ├── cli_runner.py           # Claude CLI executor
│   ├── webhook_engine.py       # Webhook processing logic
│   ├── websocket_hub.py        # WebSocket manager
│   └── database/               # Database layer
├── shared/                     # Shared models
│   └── machine_models.py       # Pydantic models
├── workers/                    # Background workers
│   └── task_worker.py          # Task processor
├── services/                   # Services
│   ├── dashboard/              # Dashboard frontend (v1)
│   └── dashboard-v2/            # Dashboard frontend (v2 - React)
├── tests/                      # Test suite
├── data/                       # Persistent data (mapped to /data)
├── main.py                     # Application entry
├── pyproject.toml              # Dependencies
├── Dockerfile                  # Container image
└── docker-compose.yml          # Multi-container setup
```

## Business Logic & Domain Models

All business rules are enforced in Pydantic models (`shared/machine_models.py`):

### 1. Task Model - Task Lifecycle Management
- Status transitions: `QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED`
- Automatic timing and duration calculation
- Cost and token usage tracking

### 2. Conversation Model - Persistent Chat History
- `ConversationDB`: Title, user_id, updated_at
- `ConversationMessageDB`: Role (user/assistant), content, metadata
- Automatic context retrieval for agent prompts (last 20 messages)

### 3. Session Model - User Session Tracking
- Tracks total cost and active tasks per user session

### 4. Webhook Models - Dynamic Configuration
- `WebhookConfig`: Provider, secret, enabled status
- `WebhookCommand`: Trigger, action, template, priority

## Core Components

### 1. Brain (Main Orchestrator)

The Brain is the main Claude CLI instance that:
- Manages sub-agents
- Handles simple queries directly
- Routes complex tasks to specialized agents
- Manages system configuration and webhooks

**Location**: `.claude/agents/brain.md`  
**Model**: opus  
**Skills**: webhook-management

### 2. Specialized Agents

#### Planning Agent
- Analyzes bugs and issues
- Creates detailed fix plans (PLAN.md)
- Does NOT implement code
- **Location**: `.claude/agents/planning.md`  
**Model**: opus  
**Tools**: Read-only (Read, Grep, FindByName, ListDir)

#### Executor Agent
- Implements code changes following TDD workflow
- Runs tests (unit, integration, E2E)
- Creates pull requests
- **Location**: `.claude/agents/executor.md`  
**Model**: sonnet  
**Skills**: testing  
**Workflow**: Red → Green → Refactor → Resilience → Acceptance → Regression → E2E

#### Service Integrator Agent
- Integrates with external services (GitHub, Jira, Slack, Sentry)
- Orchestrates cross-service workflows
- **Location**: `.claude/agents/service-integrator.md`  
**Model**: sonnet  
**Skills**: github-operations, jira-operations, slack-operations, sentry-operations

#### Self-Improvement Agent
- Analyzes codebase for patterns and improvements
- Identifies refactoring opportunities
- **Location**: `.claude/agents/self-improvement.md`  
**Model**: sonnet  
**Skills**: pattern-learner, refactoring-advisor

#### Agent Creator Agent
- Creates new agents with proper configuration
- Validates agent structure and frontmatter
- **Location**: `.claude/agents/agent-creator.md`  
**Model**: sonnet  
**Skills**: agent-generator

#### Skill Creator Agent
- Creates new skills following best practices
- Validates skill structure and organization
- **Location**: `.claude/agents/skill-creator.md`  
**Model**: sonnet  
**Skills**: skill-generator

### 3. Task Worker

Processes tasks from Redis queue:
1. Pops task from queue
2. Spawns Claude CLI from appropriate directory
3. Streams output to WebSocket
4. Saves results to database

## Process Flows

### Dashboard Chat Flow
1. User selects/creates a **Conversation**
2. User sends message via Dashboard
3. Message saved to `ConversationMessageDB`
4. **Context** (last 20 messages) retrieved and formatted
5. **Task** created in SQLite (status=QUEUED)
6. Task ID pushed to **Redis Queue**
7. **TaskWorker** pops task, marks as RUNNING
8. Claude CLI spawned in `app_dir`
9. Output streamed real-time via **WebSocket** and buffered in Redis
10. Task completes; results saved; status updated to COMPLETED
11. Response added back to **Conversation**

### Unified Webhook Flow
1. Webhook received (e.g., `/webhooks/github/webhook-123`)
2. HMAC signature verified (if configured)
3. Payload matched against **WebhookCommands**
4. Actions executed in **Priority Order**:
   - `github_reaction`: Add 👀 or 👍
   - `github_label`: Add labels like "bot-processing"
   - `create_task`: Create agent task with template rendering
   - `comment`: Post acknowledgment back to source
5. TaskWorker processes created tasks as usual

### 4. Dashboard

Real-time web interface with persistent conversation system:
- **Chat with Brain**: Inbox-style interface with full history
- **Persistent Context**: Agent automatically remembers last 20 messages
- **Task Linking**: Every message linked to underlying task for traceability
- **Monitor active tasks**: Real-time status updates
- **View costs and metrics**: Per-task and per-session tracking
- **Manage agents and webhooks**: Dynamic configuration

**Access**: `http://localhost:8000`

#### Conversation Features
- **Inbox Sidebar**: Create, rename, delete, and switch between multiple conversations
- **Context Awareness**: The agent remembers conversation history automatically
- **Traceability**: Click on any message to view execution details and logs
- **UI Usage**: Found in the **Chat** tab; click **➕** to start a new thread

### 5. Unified Webhook System

A powerful, user-configurable webhook system for GitHub, Jira, Slack, and generic sources.

#### Supported Actions
- `create_task`: Queue a task for an agent (Planning, Executor, Brain)
- `comment`: Post a response message back to the provider
- `github_reaction`: Add reactions (👀, 👍, etc.) to GitHub comments
- `github_label`: Automatically label GitHub issues/PRs
- `ask`: Request clarification from a user
- `forward`: Send event data to another service

#### Pre-built Templates
- **GitHub Issue Tracking**: Auto-triage, label, and analyze new issues
- **GitHub PR Review**: Automated code review on PR open
- **GitHub Mention Bot**: Respond to `@agent` mentions in comments
- **Jira Sync**: Automatically create agent tasks from Jira tickets

#### Webhook Endpoints
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

1. **Pydantic Everywhere**: All business logic enforced via Pydantic models
2. **On-Demand CLI**: Claude CLI spawned per request, not always running
3. **Delegation Pattern**: Brain delegates complex tasks to specialized agents
4. **Type Safety**: Full typing with mypy strict mode
5. **Asyncio Native**: All I/O operations are async
6. **TDD**: Tests for business logic first

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
