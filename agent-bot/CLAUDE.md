# Agent Bot - Containerized Multi-Agent System

> Production-ready containerized AI agent system integrating `claude-code-agent` business logic with microservices architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         External Services                                    │
│                   (GitHub, Jira, Slack, Sentry)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │     API Gateway :8000         │
                    │     (Webhook Reception)       │
                    └───────────────────────────────┘
                       │                    │
                       ▼                    ▼
                ┌──────────┐       ┌────────────────┐
                │  Redis   │       │ Knowledge      │
                │  :6379   │       │ Graph :4000    │
                └──────────┘       └────────────────┘
                       │
                       ▼
     ┌──────────────────────────────────────────────────────────────────┐
     │              Agent Engine :8080-8089 (Scalable)                  │
     │  ┌────────────────────────────────────────────────────────────┐ │
     │  │  agent-engine-package/                                      │ │
     │  │  ├── core/ (CLI providers: Claude, Cursor)                  │ │
     │  │  ├── agents/ (13 specialized agents)                        │ │
     │  │  ├── skills/ (9 reusable capabilities)                      │ │
     │  │  └── memory/ (self-improvement)                             │ │
     │  └────────────────────────────────────────────────────────────┘ │
     │  ┌────────────────────────────────────────────────────────────┐ │
     │  │  mcp.json → SSE connections to MCP servers                  │ │
     │  └────────────────────────────────────────────────────────────┘ │
     └──────────────────────────────────────────────────────────────────┘
                       │ (SSE Connections)
                       ▼
     ┌──────────────────────────────────────────────────────────────────┐
     │                   MCP Servers (4 Containers)                     │
     │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
     │  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │               │
     │  │  :9001  │ │  :9002  │ │  :9003  │ │  :9004  │               │
     │  │(Official)│ │(FastMCP)│ │(FastMCP)│ │(FastMCP)│               │
     │  └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
     └──────────────────────────────────────────────────────────────────┘
                       │ (HTTP API Calls)
                       ▼
     ┌──────────────────────────────────────────────────────────────────┐
     │                   API Services (4 Containers)                    │
     │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
     │  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │               │
     │  │  :3001  │ │  :3002  │ │  :3003  │ │  :3004  │               │
     │  └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
     └──────────────────────────────────────────────────────────────────┘
                       │
                       ▼
     ┌──────────────────────────────────────────────────────────────────┐
     │                      Dashboard Layer                             │
     │  ┌─────────────────────────┐ ┌──────────────────────────┐       │
     │  │ Internal Dashboard API  │ │ External Dashboard       │       │
     │  │ :5000                   │ │ (React) :3002            │       │
     │  └─────────────────────────┘ └──────────────────────────┘       │
     └──────────────────────────────────────────────────────────────────┘
                       │
                       ▼
     ┌──────────────────────────────────────────────────────────────────┐
     │                        Data Layer                                │
     │  ┌─────────────────────────┐ ┌──────────────────────────┐       │
     │  │   PostgreSQL :5432      │ │     Redis :6379          │       │
     │  └─────────────────────────┘ └──────────────────────────┘       │
     └──────────────────────────────────────────────────────────────────┘
```

---

## Container Inventory (14 Total)

| Service | Port | Container Name | Purpose |
|---------|------|----------------|---------|
| Agent Engine | 8080-8089 | agent-engine-{1..N} | Task execution (scalable) |
| API Gateway | 8000 | api-gateway | Webhook reception |
| GitHub MCP | 9001 | github-mcp | Official GitHub MCP |
| Jira MCP | 9002 | jira-mcp | Custom Jira MCP (FastMCP) |
| Slack MCP | 9003 | slack-mcp | Custom Slack MCP (FastMCP) |
| Sentry MCP | 9004 | sentry-mcp | Custom Sentry MCP (FastMCP) |
| GitHub API | 3001 | github-api | GitHub API wrapper |
| Jira API | 3002 | jira-api | Jira API wrapper |
| Slack API | 3003 | slack-api | Slack API wrapper |
| Sentry API | 3004 | sentry-api | Sentry API wrapper |
| Internal Dashboard | 5000 | internal-dashboard-api | Agent management API |
| External Dashboard | 3002 | external-dashboard | React monitoring UI |
| Knowledge Graph | 4000 | knowledge-graph | Entity relationships (Rust) |
| PostgreSQL | 5432 | postgres | Persistent storage |
| Redis | 6379 | redis | Task queue + cache |

---

## Key Commands

### Development Setup

```bash
make init                    # Initialize project
make build                   # Build all containers
make up                      # Start all services
make down                    # Stop all services
make logs                    # View all logs
make test                    # Run all tests
make test-unit               # Run unit tests
make test-integration        # Run integration tests
```

### Docker Operations

```bash
docker-compose up -d                          # Start all services
docker-compose up -d --scale agent-engine=3   # Scale agent engines
docker-compose logs -f agent-engine           # Follow agent logs
docker-compose exec agent-engine bash         # Shell into container
```

### Testing

```bash
cd agent-engine-package && pytest            # Test agent engine package
cd api-gateway && pytest                     # Test API gateway
cd mcp-servers/jira-mcp && pytest           # Test Jira MCP
```

---

## Project Structure

```
agent-bot/
├── CLAUDE.md                           # This file (root documentation)
├── docker-compose.yml                  # Main orchestration
├── Makefile                            # Dev commands
├── .env.example
│
├── agent-engine-package/               # Core agent engine (Python package)
│   ├── pyproject.toml
│   ├── agent_engine/
│   │   ├── core/                       # CLI providers, worker, queue
│   │   │   ├── cli/
│   │   │   │   ├── base.py             # CLIProvider protocol
│   │   │   │   ├── executor.py         # Provider factory
│   │   │   │   └── providers/
│   │   │   │       ├── claude/         # Claude Code CLI
│   │   │   │       └── cursor/         # Cursor CLI
│   │   │   ├── worker.py               # Task worker
│   │   │   ├── queue_manager.py        # Redis queue
│   │   │   └── config.py               # Settings
│   │   ├── models/                     # SQLAlchemy models
│   │   ├── agents/                     # 13 specialized agents
│   │   ├── skills/                     # 9 skill definitions
│   │   └── memory/                     # Self-improvement
│   └── tests/
│
├── agent-engine/                       # Agent engine container
│   ├── Dockerfile
│   ├── CLAUDE.md
│   └── mcp.json                        # MCP server connections
│
├── api-gateway/                        # Webhook reception
│   ├── Dockerfile
│   ├── CLAUDE.md
│   └── webhooks/                       # GitHub, Jira, Slack, Sentry
│
├── mcp-servers/                        # MCP protocol servers
│   ├── docker-compose.mcp.yml
│   ├── github-mcp/                     # Official GitHub MCP
│   ├── jira-mcp/                       # Custom FastMCP
│   ├── slack-mcp/                      # Custom FastMCP
│   └── sentry-mcp/                     # Custom FastMCP
│
├── api-services/                       # REST API wrappers
│   ├── docker-compose.services.yml
│   ├── github-api/
│   ├── jira-api/
│   ├── slack-api/
│   └── sentry-api/
│
├── internal-dashboard-api/             # Dashboard API
├── external-dashboard/                 # React dashboard
├── knowledge-graph/                    # Entity graph (Rust)
└── docs/                               # Documentation
```

---

## CLI Provider Architecture

The agent engine supports multiple CLI providers:

### Claude Code CLI (Default)

```python
CLI_PROVIDER=claude
```

Features:
- Headless execution with `--dangerously-skip-permissions`
- JSON streaming output with `--output-format stream-json`
- Real-time output via asyncio.Queue
- Cost/token tracking from result events

### Cursor CLI

```python
CLI_PROVIDER=cursor
```

Features:
- Headless execution via Cursor CLI
- Compatible streaming output format
- Same interface as Claude provider

### Provider Interface

```python
@runtime_checkable
class CLIProvider(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        timeout_seconds: int,
        model: str | None,
        allowed_tools: str | None,
    ) -> CLIResult:
        ...
```

---

## Agent System (13 Agents)

### Core Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `brain` | opus | Central orchestrator, task routing |
| `planning` | opus | Discovery + PLAN.md generation |
| `executor` | sonnet | TDD implementation |
| `verifier` | opus | Script-based verification |

### Workflow Agents

| Agent | Trigger | Response Target |
|-------|---------|-----------------|
| `github-issue-handler` | GitHub issue opened/commented | GitHub issue comment |
| `github-pr-review` | PR opened, `@agent review` | GitHub PR comment |
| `jira-code-plan` | Jira assignee changed | Jira ticket comment |
| `slack-inquiry` | Slack code questions | Slack thread reply |

### Support Agents

| Agent | Purpose |
|-------|---------|
| `service-integrator` | External service coordination |
| `self-improvement` | Memory + learning |
| `agent-creator` | Dynamic agent generation |
| `skill-creator` | Dynamic skill generation |
| `webhook-generator` | Webhook configuration |

---

## Skills System (9 Skills)

| Skill | Purpose |
|-------|---------|
| `discovery` | Code discovery and search |
| `testing` | TDD phase management |
| `code-refactoring` | Systematic refactoring |
| `github-operations` | GitHub API + response posting |
| `jira-operations` | Jira API + response posting |
| `slack-operations` | Slack API + response posting |
| `human-approval` | Approval workflow |
| `verification` | Quality verification |
| `webhook-management` | Webhook configuration |

---

## Quality Gates

### Approval Gate

Required for workflows with code changes:
- GitHub: `@agent approve` / `LGTM`
- Slack: Approve button
- Timeout: 24h → escalate

### Verification Loop

```
max_iterations = 3
if score >= 90%: complete + learn
elif iteration < 3: retry with gaps
else: escalate
```

---

## Webhook Flow

```
1. External Service sends webhook
2. API Gateway validates signature
3. API Gateway extracts routing metadata
4. Task created in PostgreSQL
5. Task queued in Redis
6. Agent Engine picks up task
7. CLI provider executes with prompt
8. Agent uses MCP servers for external calls
9. Result posted back to source
10. Dashboard updated via WebSocket
```

---

## Response Routing

| Source | Handler | Method |
|--------|---------|--------|
| GitHub | `handle_github_task_completion` | `post_pr_comment()` / `post_issue_comment()` |
| Jira | `handle_jira_task_completion` | `post_comment()` |
| Slack | `handle_slack_task_completion` | `post_message()` with `thread_ts` |

Loop prevention via Redis tracking of posted message IDs.

---

## Development Rules

### File Size Limits

Maximum 300 lines per Python file. Split into:
- `constants.py` - Constants and enums
- `models.py` - Pydantic/SQLAlchemy models
- `exceptions.py` - Custom exceptions
- `core.py` - Main logic

### Type Safety

- NO `any` types
- `ConfigDict(strict=True)` for Pydantic models
- Explicit return types on all functions
- Use `Literal` for string enums

### Code Style

- NO comments in code (self-explanatory naming)
- Docstrings only for public APIs
- Extract complex logic to named functions
- Descriptive variable/function names

### Testing Requirements

- TDD approach: test → fail → implement → pass
- Tests must run fast (< 5 seconds per file)
- No real network calls (use mocks)
- `pytest-asyncio` for async tests

### Async/Await

- Always use async/await for I/O
- `httpx.AsyncClient` instead of `requests`
- `asyncio.gather()` for parallel operations

### Structured Logging

```python
logger.info("task_started", task_id=task_id, user_id=user_id)
```

---

## Environment Variables

```bash
# CLI Provider
CLI_PROVIDER=claude                    # or 'cursor'

# Database
POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0

# API Keys (per service)
GITHUB_TOKEN=ghp_xxx
JIRA_API_TOKEN=xxx
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
SLACK_BOT_TOKEN=xoxb-xxx
SENTRY_DSN=https://xxx@sentry.io/xxx

# Webhook Secrets
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx

# Services URLs (for MCP servers)
GITHUB_API_URL=http://github-api:3001
JIRA_API_URL=http://jira-api:3002
SLACK_API_URL=http://slack-api:3003
SENTRY_API_URL=http://sentry-api:3004
```

---

## MCP Configuration (agent-engine/mcp.json)

```json
{
  "mcpServers": {
    "github": {
      "url": "http://github-mcp:9001/sse",
      "transport": "sse"
    },
    "jira": {
      "url": "http://jira-mcp:9002/sse",
      "transport": "sse"
    },
    "slack": {
      "url": "http://slack-mcp:9003/sse",
      "transport": "sse"
    },
    "sentry": {
      "url": "http://sentry-mcp:9004/sse",
      "transport": "sse"
    }
  }
}
```

---

## External Resources

- **GitHub MCP**: https://github.com/github/github-mcp-server
- **Knowledge Graph**: https://gitlab.com/gitlab-org/rust/knowledge-graph
- **Cursor CLI**: https://cursor.com/docs/cli/headless

---

## Implementation Documents

- `INTEGRATION-IMPLEMENTATION-PLAN.md` - Full TDD implementation plan
- `ARCHITECTURE.md` - Detailed architecture documentation
- `IMPLEMENTATION-PLAN.md` - Phase-by-phase breakdown
- `IMPLEMENTATION-TASKS.md` - Task checklist

---

## Health Checks

```bash
curl http://localhost:8000/health          # API Gateway
curl http://localhost:8080/health          # Agent Engine
curl http://localhost:9001/health          # GitHub MCP
curl http://localhost:9002/health          # Jira MCP
curl http://localhost:5000/health          # Dashboard API
```

---

## Troubleshooting

### Services Not Starting

1. Check Docker: `docker-compose ps`
2. Check Redis: `docker-compose exec redis redis-cli PING`
3. View logs: `docker-compose logs -f <service>`

### Tasks Not Processing

1. Check queue: `docker-compose exec redis redis-cli LLEN agent:tasks:queue`
2. Check worker: `docker-compose logs -f agent-engine`
3. Check CLI: `docker-compose exec agent-engine claude --version`

### Webhook Issues

1. Verify signature: Check `GITHUB_WEBHOOK_SECRET` matches
2. Check routing: View `api-gateway` logs
3. Test endpoint: `curl -X POST http://localhost:8000/webhooks/github`
