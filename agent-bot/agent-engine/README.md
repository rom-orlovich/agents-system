# Agent Engine Service

> Scalable task execution engine with multi-CLI provider support (Claude Code CLI and Cursor CLI).

## Purpose

The Agent Engine consumes tasks from Redis queue, executes them using CLI providers (Claude/Cursor), orchestrates 13 specialized agents, and posts results back to sources.

## Architecture

```
Redis Queue (agent:tasks)
         │
         ▼
┌─────────────────────────────────────┐
│      Agent Engine :8080-8089        │
│                                     │
│  1. Pop task from Redis            │
│  2. Update status: in_progress      │
│  3. Select CLI provider             │
│  4. Build agent prompt              │
│  5. Execute CLI with prompt        │
│  6. Stream output to Redis/WS      │
│  7. Capture result (cost, tokens)  │
│  8. Update status: completed        │
│  9. Trigger response posting       │
└─────────────────────────────────────┘
         │
         ▼
    Task Result → github-api/jira-api/slack-api
```

## Folder Structure

```
agent-engine/
├── main.py                    # FastAPI app + task worker
├── cli/
│   ├── base.py                # CLIProvider protocol
│   ├── factory.py             # Provider factory
│   ├── sanitization.py        # Output sanitization
│   └── providers/
│       ├── claude.py          # Claude CLI provider
│       └── cursor.py          # Cursor CLI provider
├── config/
│   └── settings.py            # Configuration
├── .claude/
│   ├── agents/                # 13 agent definitions
│   ├── skills/                # 9 skill definitions
│   └── CLAUDE.md              # Agent orchestration config
├── mcp.json                   # MCP server connections
└── tests/                     # Co-located tests
    ├── factories/             # Test data factories
    │   ├── task_factory.py    # Task model and factory
    │   └── session_factory.py # Session model and factory
    ├── conftest.py            # Shared fixtures
    └── test_*.py              # Test files
```

## Testing

Tests are co-located with the service for portability.

```bash
# From agent-bot root
make test-agent-engine

# Or directly
cd agent-bot
PYTHONPATH=agent-engine:$PYTHONPATH uv run pytest agent-engine/tests/ -v
```

### Test Factories

Test factories are in `tests/factories/`:

```python
from .factories import TaskFactory, SessionFactory, TaskStatus
from .factories.task_factory import InvalidTransitionError, VALID_TRANSITIONS
```

## Business Logic

### Core Responsibilities

1. **Task Consumption**: Polls Redis queue (`BRPOP agent:tasks`)
2. **CLI Execution**: Spawns CLI provider with agent prompts
3. **Agent Orchestration**: Routes to 13 specialized agents
4. **Output Streaming**: Streams to Redis Pub/Sub + WebSocket
5. **Result Processing**: Captures cost, tokens, stdout, stderr
6. **Response Posting**: Triggers posting via api-services
7. **Health Monitoring**: Logs CLI health to PostgreSQL

### Agent System (13 Agents)

**Core Agents**:

- `brain` (opus) - Central orchestrator
- `planning` (opus) - Discovery + PLAN.md
- `executor` (sonnet) - TDD implementation
- `verifier` (opus) - Quality verification

**Workflow Agents**:

- `github-issue-handler` - GitHub issues/comments
- `github-pr-review` - PR reviews
- `jira-code-plan` - Jira tickets
- `slack-inquiry` - Slack questions

**Support Agents**:

- `service-integrator` - External service coordination
- `self-improvement` - Memory + learning
- `agent-creator` - Dynamic agent generation
- `skill-creator` - Dynamic skill generation
- `webhook-generator` - Webhook configuration

### Skills System (9 Skills)

- `discovery` - Code discovery and search
- `testing` - TDD phase management
- `code-refactoring` - Systematic refactoring
- `github-operations` - GitHub API + response posting
- `jira-operations` - Jira API + response posting
- `slack-operations` - Slack API + response posting
- `human-approval` - Approval workflow
- `verification` - Quality verification
- `webhook-management` - Webhook configuration

## CLI Providers

### Claude Code CLI

```bash
claude -p --output-format stream-json --dangerously-skip-permissions
```

- Headless execution
- JSON streaming output
- Real-time cost/token tracking
- Model selection (opus, sonnet)

### Cursor CLI

```bash
cursor --headless --output-format json-stream
```

- Headless execution
- Compatible streaming format
- Model selection (complex vs execution)

## Environment Variables

```bash
CLI_PROVIDER=claude                    # or 'cursor'
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
ANTHROPIC_API_KEY=sk-ant-xxx           # For Claude CLI
CURSOR_API_KEY=xxx                     # For Cursor CLI
```

## MCP Configuration

Connects to MCP servers via SSE:

```json
{
  "mcpServers": {
    "github": { "url": "http://github-mcp:9001/sse", "transport": "sse" },
    "jira": { "url": "http://jira-mcp:9002/sse", "transport": "sse" },
    "slack": { "url": "http://slack-mcp:9003/sse", "transport": "sse" },
    "sentry": { "url": "http://sentry-mcp:9004/sse", "transport": "sse" }
  }
}
```

## Scaling

```bash
# Horizontal scaling
make cli-up PROVIDER=claude SCALE=3   # 3 Claude instances
make cli-up PROVIDER=cursor SCALE=2   # 2 Cursor instances

# Check status
make cli-status PROVIDER=claude

# View logs
make cli-logs PROVIDER=claude
```

Each replica independently consumes from the same Redis queue.

## CLI Health Monitoring

**Automatic Health Checks**:

- Claude: Pre-installed, tested at startup
- Cursor: Installed at runtime, tested at startup

**Database Logging**:

```sql
SELECT provider, version, status, hostname, checked_at
FROM cli_health
ORDER BY checked_at DESC
LIMIT 10;
```

## API Endpoints

| Endpoint           | Method | Purpose                |
| ------------------ | ------ | ---------------------- |
| `/health`          | GET    | Health check           |
| `/status`          | GET    | Service status         |
| `/tasks`           | POST   | Create task (internal) |
| `/tasks/{task_id}` | GET    | Get task status        |

## Response Posting

After task completion:

- **GitHub**: Via `github-api` → PR/issue comments
- **Jira**: Via `jira-api` → ticket comments
- **Slack**: Via `slack-api` → thread replies

## Health Check

```bash
curl http://localhost:8080/health
```

## Related Services

- **api-gateway**: Creates tasks and enqueues to Redis
- **mcp-servers**: Provides external service access
- **api-services**: Used for posting responses back
