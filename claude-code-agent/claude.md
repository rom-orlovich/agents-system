# Claude Code Agent - Complete Documentation

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Architecture & Business Logic](#architecture--business-logic)
4. [Process Flow](#process-flow)
5. [Core Components](#core-components)
6. [Testing](#testing)
7. [Development Workflow](#development-workflow)

---

## Overview

The Claude Code Agent is a **self-managing machine** where FastAPI runs as a persistent daemon and Claude Code CLI is spawned on-demand per request. This architecture enables:

- **Brain Orchestrator**: Main Claude CLI instance managing sub-agents
- **Dynamic Sub-Agents**: Planning and Executor agents spawned per task
- **Webhook Integration**: GitHub, Jira, Sentry support
- **Real-time Dashboard**: WebSocket-based conversational UI
- **Cost Tracking**: Per-task and per-session monitoring
- **Dual Storage**: Redis (ephemeral queue) + SQLite (persistent data)

### Key Principles

1. **Pydantic Everywhere**: All business logic enforced via Pydantic models
2. **On-Demand CLI**: Claude CLI spawned per request, not always running
3. **Type Safety**: Full typing with mypy strict mode
4. **Asyncio Native**: All I/O operations are async
5. **TDD**: Tests for business logic first

---

## Installation

**IMPORTANT**: This project exclusively uses `uv` for dependency management and task execution.

### Prerequisites

- Python 3.11+
- `uv` package manager
- Docker & Docker Compose (for production)
- Git

### Quick Start with uv

```bash
# 1. Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone <repository-url>
cd claude-code-agent

# 3. Install dependencies using uv
uv sync

# 4. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 5. Run tests to verify installation
uv run pytest tests/ -v

# 6. Run the application locally
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Using Make Commands (All use uv)

```bash
# Development
make run-local      # Run locally with uv
make test          # Run all tests with uv
make test-cov      # Run tests with coverage
make lint          # Run ruff linting
make format        # Format code with ruff

# Docker (for production)
make build         # Build Docker image
make up            # Start services
make down          # Stop services
make logs          # View logs
```

### Dependencies

Core dependencies are defined in `pyproject.toml`:

- **FastAPI**: API server
- **Pydantic**: Data validation and settings
- **Redis**: Task queue and cache
- **SQLAlchemy + aiosqlite**: Persistent storage
- **structlog**: Structured logging
- **httpx**: HTTP client
- **websockets**: Real-time communication

Dev dependencies:
- **pytest + pytest-asyncio**: Testing
- **pytest-cov**: Coverage
- **mypy**: Type checking
- **ruff**: Linting and formatting

---

## Architecture & Business Logic

### High-Level Architecture

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

### Business Logic: Domain Models

All business rules are enforced in Pydantic models (`shared/machine_models.py`):

#### 1. **Task Model** - Task Lifecycle Management

```python
class Task(BaseModel):
    task_id: str
    session_id: str
    user_id: str
    assigned_agent: Optional[str]
    agent_type: AgentType
    status: TaskStatus  # QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED
    input_message: str
    output_stream: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
```

**Business Rules**:
- Status transitions are validated (can't go from COMPLETED back to RUNNING)
- Timing fields auto-update based on status
- Cost must be non-negative
- Duration calculated automatically

#### 2. **Session Model** - User Session Tracking

```python
class Session(BaseModel):
    session_id: str
    user_id: str
    machine_id: str
    total_cost_usd: float
    total_tasks: int
    active_task_ids: List[str]
```

**Business Rules**:
- Sessions track all tasks for a user
- Costs accumulate per session
- Tasks can't be added twice

#### 3. **Webhook/Agent/Skill Models** - Dynamic Entity Management

```python
class WebhookConfig(BaseModel):
    name: str  # lowercase alphanumeric with hyphens only
    endpoint: str  # Must match /webhooks/[name] pattern
    source: Literal["github", "jira", "sentry", ...]
    commands: List[WebhookCommand]
    requires_signature: bool
```

**Business Rules**:
- Names must be valid (alphanumeric, hyphens, lowercase)
- Endpoints follow standard patterns
- Security settings enforced

### Storage Strategy

#### Redis (Ephemeral)
- **Task Queue**: `task_queue` list for FIFO processing
- **Task Status**: `task:{task_id}:status` for real-time tracking
- **Session Tasks**: `session:{session_id}:tasks` set
- **Output Buffer**: `task:{task_id}:output` for streaming

#### SQLite (Persistent)
- **Sessions**: Historical session data
- **Tasks**: Completed task records with full details
- **Cost Tracking**: Per-session and per-task costs
- **Entity Registry**: Dynamic agents, webhooks, skills

---

## Process Flow

### 1. Dashboard Chat Flow

```
User sends message via Dashboard
        ↓
POST /api/chat
        ↓
Create Session (if new)
        ↓
Create Task in SQLite (status=QUEUED)
        ↓
Push task_id to Redis queue
        ↓
TaskWorker pops task from queue
        ↓
Update Task status to RUNNING
        ↓
Spawn Claude CLI subprocess in appropriate directory
        ↓
Stream output to:
  • WebSocket (real-time to browser)
  • Redis (for buffering)
  • Accumulate in memory
        ↓
CLI completes
        ↓
Update Task with results:
  • output_stream
  • cost_usd, tokens
  • status = COMPLETED/FAILED
        ↓
Send completion event via WebSocket
        ↓
Save to SQLite
```

### 2. Webhook Flow (GitHub Example)

```
GitHub sends webhook
        ↓
POST /webhooks/github
        ↓
Verify signature (if required)
        ↓
Parse event type (issue_comment, pull_request, issues)
        ↓
Check for @agent command in comment
        ↓
Create webhook Session
        ↓
Create Task (assigned_agent="planning")
        ↓
Push to Redis queue
        ↓
[Same as Dashboard Chat Flow from here]
```

### 3. Agent Selection Flow

```
Task created with input_message
        ↓
TaskWorker._get_agent_dir(assigned_agent)
        ↓
If agent="brain" → /app/
If agent="planning" → /app/agents/planning/
If agent="executor" → /app/agents/executor/
        ↓
Claude CLI spawned in that directory
        ↓
Reads .claude/CLAUDE.md from that directory
        ↓
Executes with that agent's instructions
```

### 4. Real-time Communication Flow

```
Browser connects to WebSocket
        ↓
ws://host/ws/{session_id}
        ↓
WebSocketHub.register_connection(session_id, websocket)
        ↓
Task produces output chunk
        ↓
TaskWorker → WebSocketHub.send_to_session()
        ↓
WebSocket broadcasts to all connections in session
        ↓
Browser receives and displays output
```

---

## Core Components

### 1. Main Application (`main.py`)

**Purpose**: FastAPI application entry point

**Key Responsibilities**:
- Initialize FastAPI app with CORS, error handlers
- Lifespan management (startup/shutdown)
- Start TaskWorker on startup
- Connect/disconnect Redis
- Initialize SQLite database
- Serve static dashboard files

**Code Location**: `main.py:70-126`

### 2. Task Worker (`workers/task_worker.py`)

**Purpose**: Background worker processing tasks from Redis queue

**Key Responsibilities**:
- Poll Redis queue for new tasks
- Spawn Claude CLI subprocess per task
- Stream output in real-time
- Update task status in SQLite + Redis
- Send WebSocket events

**Process**:
```python
async def run(self):
    while self.running:
        task_id = await redis_client.pop_task(timeout=5)
        if task_id:
            await self._process_task(task_id)
```

**Code Location**: `workers/task_worker.py:18-180`

### 3. CLI Runner (`core/cli_runner.py`)

**Purpose**: Execute Claude CLI in headless mode

**Key Features**:
- Spawns subprocess with proper flags
- Parses JSON output from Claude CLI
- Streams content chunks to queue
- Extracts cost and token metrics
- Handles timeouts and errors

**Command**:
```bash
claude --print \
       --output-format json \
       --dangerously-skip-permissions \
       -p "User prompt here"
```

**Code Location**: `core/cli_runner.py:25-158`

### 4. WebSocket Hub (`core/websocket_hub.py`)

**Purpose**: Manage WebSocket connections per session

**Key Methods**:
- `register_connection(session_id, ws)`: Add connection
- `unregister_connection(session_id, ws)`: Remove connection
- `send_to_session(session_id, message)`: Broadcast to all in session
- `get_session_count()`: Active sessions
- `get_connection_count()`: Total connections

**Code Location**: `core/websocket_hub.py` (not shown but used in main.py)

### 5. Dashboard API (`api/dashboard.py`)

**Purpose**: REST API for dashboard operations

**Endpoints**:
- `GET /api/status`: Machine status
- `GET /api/sessions/{id}`: Session details
- `GET /api/tasks`: List tasks (with filters)
- `GET /api/tasks/{id}`: Task details
- `POST /api/tasks/{id}/stop`: Stop running task
- `POST /api/chat`: Send message to Brain
- `GET /api/agents`: List available agents
- `GET /api/webhooks`: List configured webhooks

**Code Location**: `api/dashboard.py:28-253`

### 6. Webhook Handlers (`api/webhooks.py`)

**Purpose**: Handle external webhook events

**Supported Webhooks**:
- GitHub (`POST /webhooks/github`)
  - `issue_comment`: Detect @agent commands
  - `issues`: Auto-create planning tasks
  - `pull_request`: Handle PR events
- Jira (`POST /webhooks/jira`)
- Sentry (`POST /webhooks/sentry`)

**Code Location**: `api/webhooks.py:19-178`

### 7. Database Layer

#### Redis Client (`core/database/redis_client.py`)
- Task queue operations
- Status tracking
- Session management
- Output buffering

#### SQLAlchemy Models (`core/database/models.py`)
- `TaskDB`: Persistent task records
- `SessionDB`: Session history
- Async SQLite with aiosqlite

---

## Testing

### Test Coverage

The project has comprehensive unit tests covering business logic:

**Run all tests with uv**:
```bash
uv run pytest tests/ -v
```

**Test Structure**:
```
tests/
├── unit/
│   └── test_models.py          # Pydantic model validation
├── integration/
│   └── test_api.py             # API endpoint tests
├── e2e/                        # End-to-end tests (planned)
└── conftest.py                 # Shared fixtures
```

### Unit Tests (`tests/unit/test_models.py`)

**Tested Business Logic**:

1. **Task Model**
   - ✅ Task creation with validation
   - ✅ Status transitions (QUEUED → RUNNING → COMPLETED)
   - ✅ Invalid transitions rejected
   - ✅ Timing auto-update (started_at, completed_at, duration)

2. **Session Model**
   - ✅ Session creation
   - ✅ Task tracking (no duplicates)
   - ✅ Cost accumulation
   - ✅ Negative cost rejection

3. **MachineConfig Model**
   - ✅ Valid machine ID (alphanumeric with hyphens)
   - ✅ Invalid machine ID rejected

4. **ClaudeCredentials Model**
   - ✅ Token expiry detection
   - ✅ Refresh needed detection
   - ✅ Auth status calculation

5. **WebhookConfig Model**
   - ✅ Webhook creation
   - ✅ Name validation (lowercase, alphanumeric, hyphens)

**Test Results**:
```
tests/unit/test_models.py::TestTaskModel::test_task_creation PASSED
tests/unit/test_models.py::TestTaskModel::test_task_status_transitions PASSED
tests/unit/test_models.py::TestTaskModel::test_task_timing_auto_update PASSED
tests/unit/test_models.py::TestSessionModel::test_session_creation PASSED
tests/unit/test_models.py::TestSessionModel::test_session_add_task PASSED
tests/unit/test_models.py::TestSessionModel::test_session_add_cost PASSED
tests/unit/test_models.py::TestMachineConfig::test_valid_machine_id PASSED
tests/unit/test_models.py::TestMachineConfig::test_invalid_machine_id PASSED
tests/unit/test_models.py::TestClaudeCredentials::test_credentials_status PASSED
tests/unit/test_models.py::TestWebhookConfig::test_webhook_creation PASSED
tests/unit/test_models.py::TestWebhookConfig::test_webhook_name_validation PASSED
```

### Integration Tests (`tests/integration/test_api.py`)

Tests API endpoints with AsyncClient:
- Health checks
- Task listing
- Agent listing
- Webhook endpoints

**Note**: Integration tests require Redis and database mocking for full coverage.

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage
uv run pytest tests/ -v --cov=. --cov-report=html

# Specific test
uv run pytest tests/unit/test_models.py::TestTaskModel::test_task_creation -v
```

---

## Development Workflow

### Setting Up Development Environment

```bash
# 1. Clone and install
git clone <repo-url>
cd claude-code-agent
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env as needed

# 3. Run tests to verify setup
uv run pytest tests/unit/ -v

# 4. Start development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality Tools

**Type Checking**:
```bash
uv run mypy . --strict
```

**Linting**:
```bash
uv run ruff check .
```

**Formatting**:
```bash
uv run ruff format .
```

### Project Structure

```
claude-code-agent/
├── .claude/                    # Brain CLAUDE.md instructions
├── agents/                     # Sub-agents (planning, executor)
│   ├── planning/
│   │   └── .claude/CLAUDE.md
│   └── executor/
│       └── .claude/CLAUDE.md
├── api/                        # FastAPI routes
│   ├── dashboard.py            # Dashboard REST API
│   ├── websocket.py            # WebSocket endpoint
│   └── webhooks.py             # Webhook handlers
├── core/                       # Core business logic
│   ├── config.py               # Pydantic Settings
│   ├── cli_runner.py           # Claude CLI executor
│   ├── background_manager.py   # Task manager
│   ├── websocket_hub.py        # WebSocket manager
│   ├── logging_config.py       # Structured logging
│   ├── exceptions.py           # Custom exceptions
│   ├── registry.py             # Entity registry
│   └── database/               # Database layer
│       ├── models.py           # SQLAlchemy models
│       └── redis_client.py     # Redis client
├── shared/                     # Shared domain models
│   └── machine_models.py       # Pydantic models (ALL BUSINESS LOGIC)
├── workers/                    # Background workers
│   └── task_worker.py          # Queue processor
├── services/                   # Additional services
│   └── dashboard/
│       └── static/             # Dashboard frontend
├── skills/                     # Brain skills
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── main.py                     # Application entry point
├── pyproject.toml              # Dependencies (uv managed)
├── Dockerfile                  # Container image
├── docker-compose.yml          # Multi-container setup
├── Makefile                    # Convenience commands
└── claude.md                   # THIS FILE
```

### Adding a New Feature

1. **Define business rules in Pydantic models** (`shared/machine_models.py`)
2. **Write unit tests** (`tests/unit/`)
3. **Implement feature** in appropriate module
4. **Add API endpoint** (if needed) in `api/`
5. **Run tests**: `uv run pytest tests/ -v`
6. **Check types**: `uv run mypy . --strict`
7. **Format code**: `uv run ruff format .`
8. **Commit and push**

---

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

# API
API_HOST=0.0.0.0
API_PORT=8000

# CORS
CORS_ORIGINS=["*"]
```

### Pydantic Settings

All configuration uses Pydantic Settings (`core/config.py`):
- Type-safe with validation
- Environment variable support
- Automatic type conversion
- Computed properties

---

## Troubleshooting

### Common Issues

**1. Tests fail with "Redis not connected"**
- Integration tests need Redis mocking
- Unit tests work without Redis
- Run: `uv run pytest tests/unit/ -v`

**2. Import errors**
- Run: `uv sync` to install dependencies
- Ensure virtual environment is activated

**3. Type errors**
- Run: `uv run mypy . --strict`
- Fix type hints as needed

**4. Claude CLI not found**
- Ensure Claude CLI is installed
- Check PATH environment variable

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with detailed output
uv run uvicorn main:app --reload --log-level debug
```

---

## Summary

The Claude Code Agent is a production-ready system for running Claude Code CLI on-demand with:

✅ **Pydantic-enforced business logic** - All rules in domain models
✅ **Async task processing** - Redis queue + background worker
✅ **Real-time streaming** - WebSocket-based dashboard
✅ **Cost tracking** - Per-task and per-session metrics
✅ **Webhook support** - GitHub, Jira, Sentry integration
✅ **Type safety** - Full mypy strict mode
✅ **Comprehensive tests** - Unit tests for all business logic
✅ **uv-based workflow** - Fast, reliable dependency management

**Always use `uv` for all operations**: `uv sync`, `uv run`, `uv add`, etc.

For issues and contributions, see the main README.md.
