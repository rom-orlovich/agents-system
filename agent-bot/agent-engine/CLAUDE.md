# Agent Engine Container

> Scalable task execution engine with multi-CLI provider support.

## Purpose

The Agent Engine container executes AI agent tasks using the configured CLI provider (Claude Code or Cursor). It consumes tasks from Redis queue and orchestrates 13 specialized agents.

## Container Details

| Property | Value |
|----------|-------|
| Port Range | 8080-8089 |
| Scalable | Yes (1-N replicas) |
| Base Image | python:3.11-slim |
| CLI Providers | Claude Code, Cursor |
| Health Monitoring | Auto-logged to PostgreSQL |

## Automatic CLI Installation

### Claude Code CLI
- Pre-installed during Docker build
- Requires: `ANTHROPIC_API_KEY`
- Test command: `claude --version`

### Cursor CLI
- Installed at runtime if `CLI_PROVIDER=cursor`
- Requires: `CURSOR_API_KEY`
- Installation: Automatic via `curl https://cursor.com/install -fsS | bash`
- Test command: `agent --version`

Both CLIs are automatically tested at startup and status is logged to the database.

## Architecture

```
Redis Queue
    │
    ▼
┌───────────────────────────────────────┐
│          Agent Engine                 │
│  ┌─────────────────────────────────┐ │
│  │      Task Worker                │ │
│  │      (Semaphore-controlled)     │ │
│  └─────────────────────────────────┘ │
│            │                          │
│            ▼                          │
│  ┌─────────────────────────────────┐ │
│  │      CLI Executor               │ │
│  │  ┌───────────┬───────────┐     │ │
│  │  │  Claude   │  Cursor   │     │ │
│  │  │  Provider │  Provider │     │ │
│  │  └───────────┴───────────┘     │ │
│  └─────────────────────────────────┘ │
│            │                          │
│            ▼                          │
│  ┌─────────────────────────────────┐ │
│  │      MCP Connections            │ │
│  │  (mcp.json → SSE servers)       │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
```

## Key Files

```
agent-engine/
├── Dockerfile
├── CLAUDE.md               # This file
├── mcp.json               # MCP server connections
├── .claude/
│   └── settings.json      # Claude CLI settings
└── main.py                # Entry point
```

## Environment Variables

```bash
CLI_PROVIDER=claude                     # or 'cursor'
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
```

## MCP Configuration

The agent engine connects to MCP servers via SSE:

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

## Task Processing Flow

1. Worker pops task from Redis queue
2. Task status updated to RUNNING
3. CLI executor invoked with prompt
4. Output streamed to Redis
5. Result posted back via completion handler
6. Task status updated to COMPLETED/FAILED

## CLI Providers

### Claude Code CLI

```bash
claude -p --output-format stream-json --dangerously-skip-permissions ...
```

Features:
- Headless execution
- JSON streaming output
- Real-time cost/token tracking

### Cursor CLI

```bash
cursor --headless --output-format json-stream ...
```

Features:
- Headless execution
- Compatible streaming format
- Same interface as Claude

## Scaling

### Using Make Commands (Recommended)

```bash
# Start with scaling
make cli-up PROVIDER=claude SCALE=3   # 3 Claude instances
make cli-up PROVIDER=cursor SCALE=2   # 2 Cursor instances

# Check status
make cli-status PROVIDER=claude

# View logs
make cli-logs PROVIDER=claude

# Stop
make cli-down PROVIDER=claude
```

### Using Docker Compose

```bash
# Scale with specific project name
CLI_PROVIDER=claude docker-compose -p claude up -d --scale cli=5

# Scale existing deployment
docker-compose up -d --scale agent-engine=3
```

Each replica independently consumes from the same Redis queue.

## CLI Health Monitoring

### Startup Health Checks

Every container automatically checks CLI health on startup:

**Claude:**
```
Testing Claude CLI access...
✅ CLI version check passed
Starting main application as agent user...
```

**Cursor:**
```
Installing Cursor CLI for agent user...
✅ Cursor CLI installed successfully
Testing Cursor CLI access...
✅ Cursor CLI available: 2026.01.28-fd13201
Starting main application as agent user...
```

### Database Logging

Health status is automatically logged to `cli_health` table:

```sql
CREATE TABLE cli_health (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    version VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    hostname VARCHAR(255),
    checked_at TIMESTAMP DEFAULT NOW()
);
```

**Query health history:**
```bash
docker-compose exec postgres psql -U agent -d agent_system -c "
  SELECT provider, version, status, hostname, checked_at
  FROM cli_health
  ORDER BY checked_at DESC
  LIMIT 10;
"
```

### Scripts

- `scripts/test_cli_after_build.py` - Claude CLI version and API test
- `scripts/log_cli_status.py` - Log CLI status to database
- `scripts/docker-start.sh` - Startup orchestration with health checks

## Health Check

```bash
curl http://localhost:8080/health
```

## Logs

```bash
# Using make
make cli-logs PROVIDER=claude

# Using docker-compose
docker-compose logs -f agent-engine
```

## Development

```bash
cd agent-engine-package
pip install -e ".[dev]"
pytest
```
