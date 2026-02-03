# Agent Engine

The core execution service that processes AI tasks using CLI providers (Claude Code or Cursor).

## Purpose

Agent Engine is the central task processing service that:

1. **Consumes Tasks** from Redis queue (`agent:tasks`)
2. **Routes to CLI Provider** (Claude Code or Cursor)
3. **Manages Concurrency** with configurable parallelism
4. **Reports Status** via Redis pub/sub and hashes
5. **Integrates Knowledge** (optional) from knowledge services

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Engine                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   FastAPI    │    │  TaskWorker  │    │  Knowledge   │       │
│  │   Server     │───▶│   (async)    │───▶│   Service    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    REST      │    │     CLI      │    │  LlamaIndex  │       │
│  │    API       │    │   Factory    │    │     GKG      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                             │                                    │
│                             ▼                                    │
│                      ┌──────────────┐                           │
│                      │   Claude     │   ┌──────────────┐        │
│                      │   Cursor     │   │    Model     │        │
│                      │   Provider   │───│   Selection  │        │
│                      └──────────────┘   └──────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### TaskWorker (`main.py`)

- Async worker consuming from Redis queue
- Semaphore-based concurrency control
- Task status updates via Redis pub/sub

### CLI Providers (`cli/providers/`)

- **Claude**: Uses `claude` CLI with MCP tools
- **Cursor**: Uses `cursor` CLI alternative
- Both implement `CLIProviderProtocol`

### Knowledge Service (`services/knowledge.py`)

- **Optional integration** - disabled by default
- Graceful degradation (returns empty results if unavailable)
- Connects to LlamaIndex and Graph Knowledge Graph (GKG)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Detailed component status |
| `/status` | GET | Worker and service status |
| `/tasks` | POST | Queue new task |
| `/tasks/{task_id}` | GET | Get task status/result |
| `/knowledge/toggle` | POST | Enable/disable knowledge |

## Configuration

Environment variables (via `config/settings.py`):

```bash
# Core Settings
PORT=8080
CLI_PROVIDER=claude              # "claude" or "cursor"
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Knowledge Services (optional)
KNOWLEDGE_SERVICES_ENABLED=false
LLAMAINDEX_URL=http://llamaindex-service:8100
KNOWLEDGE_GRAPH_URL=http://gkg-service:4000
KNOWLEDGE_TIMEOUT_SECONDS=10.0
KNOWLEDGE_RETRY_COUNT=2

# Model Selection
CLAUDE_MODEL_COMPLEX=opus        # For planning tasks
CLAUDE_MODEL_EXECUTION=sonnet    # For execution tasks
CURSOR_MODEL_COMPLEX=claude-sonnet-4.5
CURSOR_MODEL_EXECUTION=composer-1
```

## Task Flow

```
1. Task arrives → POST /tasks
         │
         ▼
2. Queued in Redis → LPUSH agent:tasks
         │
         ▼
3. Worker picks up → BRPOP agent:tasks
         │
         ▼
4. Status: in_progress → HSET + PUBLISH
         │
         ▼
5. Route to CLI → run_cli(prompt, repo_path)
         │
         ├─ Simple task → sonnet/composer-1
         └─ Complex task → opus/claude-sonnet-4.5
         │
         ▼
6. Status: completed/failed → HSET + PUBLISH
```

## Task Types & Model Routing

| Agent Type | Model (Claude) | Model (Cursor) |
|------------|---------------|----------------|
| planning | opus | claude-sonnet-4.5 |
| consultation | opus | claude-sonnet-4.5 |
| question_asking | opus | claude-sonnet-4.5 |
| brain | opus | claude-sonnet-4.5 |
| execution | sonnet | composer-1 |
| (default) | sonnet | composer-1 |

## Independence Principle

Agent Engine works **independently** without knowledge services:

```python
# When KNOWLEDGE_SERVICES_ENABLED=false
knowledge_service = NoopKnowledgeService()  # Returns empty results
```

This allows:
- Testing agent logic without knowledge dependencies
- Gradual rollout of knowledge features
- Isolated debugging and development

## Commands

```bash
# Run locally
uv run python main.py

# Run tests
uv run pytest tests/ -v

# Test specific component
uv run pytest tests/test_task_lifecycle.py -v

# Run with knowledge services
KNOWLEDGE_SERVICES_ENABLED=true uv run python main.py
```

## Testing

Tests focus on **behavior**, not implementation:

- `test_task_lifecycle.py` - Task processing flow
- `test_session_management.py` - Session handling
- `test_cli_provider_selection.py` - Provider routing
- `test_knowledge_service.py` - Knowledge integration

## Dependencies

- **Redis**: Task queue and status storage
- **PostgreSQL**: Indirect via dashboard-api
- **CLI Provider**: Claude Code or Cursor CLI installed
- **Knowledge Services** (optional): LlamaIndex, GKG
