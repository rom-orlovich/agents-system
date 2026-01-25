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
- 💬 **Persistent Conversations**: Inbox-style UI with context awareness (Dashboard v2)
- 🔄 **Task Flow Tracking**: End-to-end flow tracking with flow_id across webhook → analysis → execution
- 📡 **Unified Webhooks**: Fully configurable GitHub, Jira, Slack, Sentry integration
- 🤖 **9 Specialized Agents**: Brain, Planning, Executor, Service Integrator, Self-Improvement, Agent Creator, Skill Creator, Verifier, Webhook Generator
- 📊 **Advanced Analytics**: Cost tracking, usage metrics, OAuth monitoring, conversation analytics
- 🗄️ **Dual Storage**: Redis (queue/cache) + SQLite (persistence)
- 🔌 **Hybrid Webhooks**: Static routes (hard-coded) + Dynamic routes (database-driven)
- 🧪 **TDD Workflow**: Full test-driven development with E2E validation
- 🔗 **Service Integration**: Cross-service workflows (GitHub, Jira, Slack, Sentry)
- 📁 **Claude Code Tasks Integration**: Background agents read task directory for visibility without context injection
- 🎨 **Modern Dashboard v2**: React-based UI with Overview, Analytics, Ledger, Webhooks, Chat, and Registry features
- 📈 **Real-time Monitoring**: WebSocket-based live updates, task logs, system metrics
- 🔐 **Multi-Account Support**: Account management, credential handling, OAuth usage tracking

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

5. Access the dashboard v2:
```
http://localhost:8000
```

The dashboard v2 is a modern React-based interface with 6 main features: Overview, Analytics, Ledger, Webhooks, Chat, and Registry.

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
│   ├── webhooks/               # Static webhook handlers (hard-coded)
│   │   ├── github.py          # GitHub webhook handler
│   │   ├── jira.py            # Jira webhook handler
│   │   ├── slack.py           # Slack webhook handler
│   │   └── sentry.py          # Sentry webhook handler
│   ├── webhooks_dynamic.py     # Dynamic webhook receiver (database-driven)
│   ├── webhook_status.py       # Webhook status/monitoring API
│   └── ...                     # Other API endpoints
├── core/                       # Core logic
│   ├── config.py               # Configuration
│   ├── cli_runner.py           # Claude CLI executor
│   ├── webhook_configs.py      # Static webhook configurations
│   ├── webhook_engine.py       # Shared webhook utilities (render_template, etc.)
│   ├── websocket_hub.py        # WebSocket manager
│   └── database/               # Database layer
├── shared/                     # Shared models
│   └── machine_models.py       # Pydantic models
├── workers/                    # Background workers
│   └── task_worker.py          # Task processor
├── services/                   # Services
│   ├── dashboard/              # Dashboard frontend (v1 - Legacy)
│   └── dashboard-v2/            # Dashboard frontend (v2 - React + TypeScript)
│       ├── src/
│       │   ├── features/       # Feature modules
│       │   │   ├── overview/   # System overview & metrics
│       │   │   ├── analytics/  # Cost & usage analytics
│       │   │   ├── ledger/    # Transaction ledger
│       │   │   ├── webhooks/   # Webhook management
│       │   │   ├── chat/       # Chat interface
│       │   │   └── registry/  # Skills & agents registry
│       │   ├── components/    # Reusable UI components
│       │   ├── hooks/         # React hooks
│       │   └── layouts/       # Layout components
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

### 4. Webhook Models - Hybrid Configuration

**Static Webhooks** (Hard-Coded):
- `WebhookConfig`: Name, endpoint, source, commands, target_agent
- `WebhookCommand`: Name, aliases, prompt_template, target_agent
- **Location**: `core/webhook_configs.py`
- **Validation**: Pydantic models, validated at startup

**Dynamic Webhooks** (Database-Driven):
- `WebhookConfigDB`: Provider, secret, enabled status, endpoint
- `WebhookCommandDB`: Trigger, action, template, priority, conditions
- **Location**: Database (`webhook_configs` table)
- **Management**: Via `/api/webhooks` endpoints

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

### 2. Specialized Agents (9 Total)

#### Brain Agent (Main Orchestrator)
- Coordinates all system operations
- Delegates to specialized agents
- Manages webhooks and system configuration
- **Location**: `.claude/agents/brain.md`  
**Model**: opus  
**Skills**: webhook-management

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

#### Verifier Agent
- Validates implementations and test results
- Performs final verification checks
- **Location**: `.claude/agents/verifier.md`

#### Webhook Generator Agent
- Creates and configures webhooks dynamically
- Manages webhook templates and commands
- **Location**: `.claude/agents/webhook-generator.md`

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

### Task Flow Conversation Tracking

Each initiated task flow (e.g., Jira ticket assignment) creates a special `flow_id` that tracks the entire lifecycle: webhook trigger → analysis → plan creation → PR creation → execution. All tasks in this flow belong to one conversation (unless user explicitly breaks it).

**Flow Tracking Features:**
- **Flow ID Generation**: Stable `flow_id` generated from external IDs (Jira ticket key, GitHub PR number, etc.)
- **Conversation Inheritance**: Child tasks automatically inherit parent's `conversation_id` (default behavior)
- **Conversation Breaks**: Users can explicitly start new conversations via keywords ("new conversation", "start fresh") or API flags
- **Flow ID Propagation**: `flow_id` always propagates even when conversation breaks (for end-to-end tracking)
- **Aggregated Metrics**: Dashboard shows aggregated cost, task count, and duration per conversation
- **Claude Code Tasks Integration**: Background agents read `~/.claude/tasks/` directory to see completed tasks without context injection

**Example Flow:**
```
Jira Ticket Assigned (PROJ-123)
  ↓
Generate flow_id: "flow-abc123"
  ↓
Create Task #1 (root) with flow_id, conversation_id="conv-xyz"
  ↓
Task #1 creates Task #2 (child) → Inherits conversation_id (default)
  ↓
Task #2 creates Task #3 (child) → Inherits conversation_id (default)
  ↓
All tasks update conversation metrics on completion
  ↓
Dashboard shows aggregated metrics for conversation
```

**Claude Code Tasks Integration:**
- Orchestration tasks are synced to `~/.claude/tasks/` directory (if `sync_to_claude_tasks=True`)
- Background agents can read task directory to see:
  - Which tasks are completed
  - Task dependencies
  - Task status and results
- No context injection needed - agents read task directory instead
- More efficient than injecting large conversation history

### Webhook Flow with Human Approval

```
Webhook (Jira/GitHub/Sentry)
        ↓
    Brain (classify task)
        ↓
    Planning Agent
    ├─ Invoke discovery skill
    ├─ Create PLAN.md
    ├─ Create Draft PR
    └─ Send Slack notification
        ↓
    WAIT FOR HUMAN APPROVAL ← Required for webhook tasks
    (GitHub: @agent approve | Slack: Approve button)
        ↓
    Executor Agent
    ├─ Verify approval exists
    ├─ TDD implementation
    └─ Update PR (remove draft)
        ↓
    Verifier Agent (loop ×3)
        ↓
    Self-Improvement Agent ← Auto-triggered on success
```

**Slack Notification includes:**
- 📖 Background - Context and why change is needed
- ✅ What Was Done - Summary of planning agent work
- 💡 Key Insights - Root cause, affected components, risk level
- 📁 Files Affected - List of files to be modified

**Approval Options:**
| Source | Approve | Reject |
|--------|---------|--------|
| GitHub PR | `@agent approve`, `LGTM` | `@agent reject` |
| Slack button | Posts `@agent approve` to PR | Posts `@agent reject` to PR |

### Static Route Flow (Hard-Coded)
1. Webhook received at `/webhooks/github` (or jira/slack/sentry)
2. Signature verified (provider-specific)
3. Command matched by name/aliases + prefix (e.g., `@agent analyze`)
4. Immediate response sent (GitHub reaction, Slack ephemeral message)
5. Task created and queued → **follows Human Approval workflow above**
6. Slack notification sent on completion

### Dynamic Route Flow (Database-Driven)
1. Webhook received at `/webhooks/{provider}/{webhook_id}`
2. HMAC signature verified (if configured)
3. Payload matched against **WebhookCommands** (trigger + conditions)
4. Actions executed in **Priority Order**:
   - `github_reaction`: Add 👀 or 👍
   - `github_label`: Add labels like "bot-processing"
   - `create_task`: Create agent task → **follows Human Approval workflow**
   - `comment`: Post acknowledgment back to source
5. TaskWorker processes created tasks with approval gate

### 4. Dashboard v2 (React-based)

Modern real-time web interface with comprehensive features:

#### Overview Tab
- **System Status**: Queue depth, active sessions, WebSocket connections, daily burn rate
- **OAuth Usage**: Session and weekly usage percentages
- **Task Monitoring**: Real-time task list with status, logs, and execution details
- **Global Logs**: System-wide log streaming

#### Analytics Tab
- **Cost Analytics**: Histogram views, cost breakdown by subagent
- **Conversation Analytics**: Conversation-level metrics and trends
- **Usage Patterns**: Task distribution and performance metrics

#### Ledger Tab
- **Transaction History**: Detailed cost and token usage per task
- **Filtering**: By date, agent, status, conversation
- **Export**: Download transaction data

#### Webhooks Tab
- **Webhook Management**: View, create, edit, delete webhooks
- **Command Configuration**: Manage webhook commands and triggers
- **Event History**: View webhook events and responses
- **Status Monitoring**: Enable/disable webhooks, view statistics

#### Chat Tab (Communications)
- **Persistent Conversations**: Inbox-style interface with full history
- **Context Awareness**: Agent automatically remembers last 20 messages
- **Task Linking**: Every message linked to underlying task for traceability
- **Real-time Updates**: WebSocket-based live message streaming
- **Conversation Management**: Create, rename, delete, and switch between conversations

#### Registry Tab
- **Skills Management**: View, upload, delete skills
- **Agents Management**: View, upload, delete agents
- **Content Editing**: Edit skill and agent content directly
- **Asset Browser**: Browse all available skills and agents

**Access**: `http://localhost:8000`

**Technology**: React + TypeScript, Tailwind CSS, React Query for data fetching

### 5. Hybrid Webhook System

A powerful webhook system using a **hybrid approach**: **static routes** (hard-coded) + **dynamic routes** (database-driven).

#### Architecture: Static + Dynamic Routes

**Static Routes (Hard-Coded)** - Recommended for production:
- ✅ Type-safe, validated at startup
- ✅ Version controlled in git
- ✅ Easy to maintain and understand
- ✅ One file per provider with all logic
- **Endpoints**: `/webhooks/github`, `/webhooks/jira`, `/webhooks/slack`, `/webhooks/sentry`
- **Location**: `api/webhooks/github.py`, `api/webhooks/jira.py`, etc.
- **Configuration**: `core/webhook_configs.py`

**Dynamic Routes (Database-Driven)** - For runtime configuration:
- ✅ Create webhooks via API
- ✅ Store in database
- ✅ Enable/disable without code changes
- **Endpoints**: `/webhooks/{provider}/{webhook_id}`
- **Location**: `api/webhooks_dynamic.py`
- **Management API**: `/api/webhooks` (CRUD operations)

#### Static Webhook Features

- **Command Matching**: By name/aliases + command prefix (e.g., `@agent analyze`)
- **Immediate Responses**: GitHub reactions, Slack ephemeral messages
- **Template Rendering**: `{{variable}}` syntax with nested access
- **Slack Notifications**: Automatic notifications on task completion
- **Type Safety**: Pydantic validation at startup

#### Dynamic Webhook Features

- **Trigger-Based**: Event type matching (e.g., `issues.opened`)
- **Condition Filtering**: Match based on payload conditions
- **Priority Ordering**: Execute commands by priority
- **Runtime Management**: Create, update, delete via API

#### Supported Actions
- `create_task`: Queue a task for an agent (Planning, Executor, Brain)
- `comment`: Post a response message back to the provider
- `github_reaction`: Add reactions (👀, 👍, etc.) to GitHub comments
- `github_label`: Automatically label GitHub issues/PRs
- `ask`: Request clarification from a user
- `forward`: Send event data to another service

#### Webhook Endpoints

**Static Routes** (Hard-Coded):
- **GitHub**: `POST /webhooks/github` - Issues, PRs, comments
- **Jira**: `POST /webhooks/jira` - Ticket updates
- **Slack**: `POST /webhooks/slack` - Commands and mentions
- **Sentry**: `POST /webhooks/sentry` - Error alerts

**Dynamic Routes** (Database-Driven):
- **GitHub**: `POST /webhooks/github/{webhook_id}`
- **Jira**: `POST /webhooks/jira/{webhook_id}`
- **Slack**: `POST /webhooks/slack/{webhook_id}`
- **Sentry**: `POST /webhooks/sentry/{webhook_id}`
- **Custom**: `POST /webhooks/custom/{webhook_id}`

## API Endpoints

### Dashboard API (v1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Machine status |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/table` | Get tasks as table rows |
| GET | `/api/tasks/{task_id}` | Get task details |
| GET | `/api/tasks/{task_id}/logs` | Get task logs |
| POST | `/api/tasks/{task_id}/stop` | Stop task |
| POST | `/api/chat` | Send message to Brain |
| GET | `/api/agents` | List agents |
| GET | `/api/webhooks` | List webhooks (static) |
| GET | `/api/webhooks/events` | List webhook events |
| GET | `/api/webhooks/stats` | Webhook statistics |

### Conversations API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get conversation details |
| PUT | `/api/conversations/{id}` | Update conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| POST | `/api/conversations/{id}/clear` | Clear conversation |
| POST | `/api/conversations/{id}/messages` | Add message |
| GET | `/api/conversations/{id}/messages` | Get messages |
| GET | `/api/conversations/{id}/metrics` | Get conversation metrics |
| GET | `/api/conversations/{id}/context` | Get conversation context |

### Webhooks API (Dynamic)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/webhooks-status` | Webhook status overview |
| GET | `/api/webhooks` | List all webhooks |
| GET | `/api/webhooks/{id}` | Get webhook details |
| POST | `/api/webhooks` | Create webhook |
| PUT | `/api/webhooks/{id}` | Update webhook |
| DELETE | `/api/webhooks/{id}` | Delete webhook |
| POST | `/api/webhooks/{id}/enable` | Enable webhook |
| POST | `/api/webhooks/{id}/disable` | Disable webhook |
| GET | `/api/webhooks/{id}/events` | Get webhook events |
| POST | `/api/webhooks/{id}/commands` | Add webhook command |
| GET | `/api/webhooks/{id}/commands` | List webhook commands |
| PUT | `/api/webhooks/{id}/commands/{cmd_id}` | Update command |
| DELETE | `/api/webhooks/{id}/commands/{cmd_id}` | Delete command |
| GET | `/api/webhooks/events/recent` | Recent webhook events |

### Analytics API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/summary` | Analytics summary |
| GET | `/api/analytics/costs/histogram` | Cost histogram |
| GET | `/api/analytics/costs/by-subagent` | Costs by subagent |
| GET | `/api/analytics/conversations` | Conversation analytics |

### Registry API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/registry/skills` | List skills |
| POST | `/api/registry/skills/upload` | Upload skill |
| DELETE | `/api/registry/skills/{name}` | Delete skill |
| GET | `/api/registry/agents` | List agents |
| POST | `/api/registry/agents/upload` | Upload agent |
| DELETE | `/api/registry/agents/{name}` | Delete agent |
| GET | `/api/registry/{asset_type}/{name}/content` | Get asset content |
| PUT | `/api/registry/{asset_type}/{name}/content` | Update asset content |

### Credentials & Accounts API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/credentials/status` | Credentials status |
| POST | `/api/credentials/upload` | Upload credentials |
| GET | `/api/credentials/cli-status` | CLI status |
| GET | `/api/credentials/usage` | OAuth usage |
| GET | `/api/credentials/accounts` | List accounts |
| POST | `/api/v2/accounts/credentials/upload` | Upload credentials (v2) |
| GET | `/api/v2/accounts` | List accounts (v2) |
| GET | `/api/v2/accounts/current` | Current account |
| GET | `/api/v2/accounts/{id}` | Get account |
| GET | `/api/v2/machines` | List machines |
| POST | `/api/v2/machines/register` | Register machine |
| GET | `/api/v2/machines/{id}` | Get machine |
| POST | `/api/v2/machines/{id}/heartbeat` | Machine heartbeat |
| POST | `/api/v2/machines/{id}/link` | Link machine to account |

### Subagents API (v2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/subagents/spawn` | Spawn subagent |
| GET | `/api/v2/subagents/active` | List active subagents |
| GET | `/api/v2/subagents/{id}` | Get subagent |
| POST | `/api/v2/subagents/{id}/stop` | Stop subagent |
| GET | `/api/v2/subagents/{id}/output` | Get subagent output |
| GET | `/api/v2/subagents/{id}/context` | Get subagent context |
| POST | `/api/v2/subagents/parallel` | Spawn parallel subagents |
| GET | `/api/v2/subagents/parallel/{group_id}/results` | Get parallel results |

### Sessions API (v2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/sessions/{id}` | Get session |
| GET | `/api/v2/sessions/{id}/status` | Session status |
| POST | `/api/v2/sessions/{id}/reset` | Reset session |
| GET | `/api/v2/sessions/summary/weekly` | Weekly summary |
| GET | `/api/v2/dashboard/session/current` | Current dashboard session |
| GET | `/api/v2/dashboard/sessions/history` | Session history |

### Container API (v2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/container/status` | Container status |
| GET | `/api/v2/container/processes` | List processes |
| GET | `/api/v2/container/resources` | Resource usage |
| POST | `/api/v2/container/processes/{pid}/kill` | Kill process |
| POST | `/api/v2/container/exec` | Execute command |

### WebSocket

- **Endpoint**: `/ws/{session_id}`
- **Events**: task.created, task.output, task.completed, task.failed

### Webhooks

**Static Routes** (Hard-Coded):
| Endpoint | Description |
|----------|-------------|
| `POST /webhooks/github` | GitHub events (hard-coded handler) |
| `POST /webhooks/jira` | Jira events (hard-coded handler) |
| `POST /webhooks/slack` | Slack events (hard-coded handler) |
| `POST /webhooks/sentry` | Sentry events (hard-coded handler) |

**Dynamic Routes** (Database-Driven):
| Endpoint | Description |
|----------|-------------|
| `POST /webhooks/{provider}/{webhook_id}` | Dynamic webhook (created via API) |
| `GET /api/webhooks` | List all webhooks |
| `POST /api/webhooks` | Create new webhook |
| `PUT /api/webhooks/{id}` | Update webhook |
| `DELETE /api/webhooks/{id}` | Delete webhook |

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

## Implementation Status

> **Overall Alignment with Business Requirements**: ~85-90%
>
> See [docs/BUSINESS-REQUIREMENTS.md](docs/BUSINESS-REQUIREMENTS.md) for detailed analysis.

### What's Working
| Feature | Status |
|---------|--------|
| Static Webhooks (GitHub, Jira, Slack, Sentry) | ✅ Full implementation |
| Dynamic Webhook CRUD | ✅ API endpoints working |
| Task Queue & Worker | ✅ Concurrent processing |
| Conversation Flow Tracking | ✅ flow_id, conversation_id |
| Dashboard v2 (React) | ✅ All 6 features implemented |
| Analytics & Cost Tracking | ✅ Comprehensive metrics |
| Registry Management | ✅ Skills & agents CRUD |
| All 9 Agents | ✅ Brain, Planning, Executor, etc. |
| Real-time WebSocket | ✅ Task streaming |
| Multi-Account Support | ✅ Account & machine management |
| OAuth Usage Tracking | ✅ Session & weekly monitoring |
| Container Management | ✅ Process & resource monitoring |

### Known Gaps
| Feature | Status | Priority |
|---------|--------|----------|
| Webhook Generator Agent | ✅ Implemented | - |
| Skill webhook_config Sync | ⚠️ Partial | P1 - High |
| Jira/Slack Signature Verification (Dynamic) | ⚠️ Partial | P1 - High |
| Response to Webhook Source (Dynamic) | ⚠️ Placeholder | P1 - High |
| Static + Dynamic Command Merging | ❌ Not implemented | P2 - Medium |
| Cloud Storage (S3/BLOB) | ❌ Local only | P2 - Medium |

### Recent Improvements
- ✅ Dashboard v2 with React + TypeScript
- ✅ Comprehensive analytics and cost tracking
- ✅ Registry management for skills and agents
- ✅ Multi-account and machine management
- ✅ Container monitoring and process management
- ✅ Enhanced conversation management
- ✅ Webhook Generator agent added

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
