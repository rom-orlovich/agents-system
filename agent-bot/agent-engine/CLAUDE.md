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
| Package | agent-engine-package |

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

```bash
docker-compose up -d --scale agent-engine=3
docker-compose up -d --scale agent-engine=5
```

Each replica independently consumes from the same Redis queue.

## Health Check

```bash
curl http://localhost:8080/health
```

## Logs

```bash
docker-compose logs -f agent-engine
```

## Development

```bash
cd agent-engine-package
pip install -e ".[dev]"
pytest
```
