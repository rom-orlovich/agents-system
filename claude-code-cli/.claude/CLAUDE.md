# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production AI agent system using Claude Code CLI for autonomous bug fixing. Two-agent architecture (Planning + Executor) that processes Sentry alerts, creates fix plans, and generates PRs after human approval.

**Flow:** Sentry Alert → Jira Ticket → Planning Agent (analysis + PLAN.md) → Human Approval → Executor Agent (TDD fix) → PR Ready

## Build & Run Commands

```bash
# Initial setup
make setup                    # Check prerequisites (Docker, Claude CLI auth)
make env                      # Create/edit .env file

# Development
make up                       # Start all services (docker-compose up -d)
make down                     # Stop all services
make restart                  # Fast restart (stop + up)
make rebuild                  # Rebuild Docker images (Run after updating pyproject.toml)
make logs                     # View all container logs
make tunnel                   # Expose port 8000 for webhooks via ngrok
make test                     # Run pytest tests
make clean                    # Remove volumes and images

# Individual service logs
cd infrastructure/docker && docker-compose logs -f planning-agent
cd infrastructure/docker && docker-compose logs -f executor-agent
cd infrastructure/docker && docker-compose logs -f webhook-server

# Agent Commands (GitHub/Slack)
- `@agent approve` : Approve plan execution
- `@agent reject [reason]` : Reject plan
- `@agent improve <feedback>` : Request changes to plan
- `@agent status` : Check task status
```

## Architecture

```
agents/
├── planning-agent/           # Analyzes bugs, creates PLAN.md, opens draft PRs
│   ├── worker.py             # Queue consumer, invokes Claude CLI with skills
│   └── skills/               # Skill prompts (SKILL.md or prompt.md)
│       ├── discovery/        # Find repo/files from error info
│       ├── jira-enrichment/  # Enrich Jira tickets from Sentry
│       ├── plan-changes/     # Handle PR feedback
│       └── execution/        # Execute approved plans
│
├── executor-agent/           # Implements fixes following TDD
│   ├── worker.py             # Queue consumer
│   └── skills/
│       ├── git-operations/   # Clone, branch, commit, push
│       ├── tdd-workflow/     # RED → GREEN → REFACTOR
│       ├── execution/        # Main orchestration
│       └── code-review/      # Self-review before commit

services/
└── webhook-server/           # FastAPI app receiving webhooks
    ├── main.py               # App entry point, /health, /metrics
    └── routes/               # jira.py, sentry.py, github.py, slack.py

shared/                       # Common utilities
├── config.py                 # Pydantic settings (env vars)
├── task_queue.py             # Redis queue operations
├── logging_utils.py          # Structured logging
├── models.py                 # Task status enums, data models
├── slack_client.py           # Slack notifications
└── metrics.py                # Prometheus metrics

infrastructure/docker/
├── docker-compose.yml        # Local dev: redis, postgres, webhook-server, agents
├── mcp.json                  # MCP server configuration
└── .env.example              # Environment template
```

## Key Patterns

### Worker Task Processing
Workers poll Redis queues, route tasks to skills, invoke Claude CLI:
```python
# agents/planning-agent/worker.py
task_data = await self.queue.pop(self.queue_name, timeout=0)
skill_prompt = self._load_skill(skill_name)  # Loads SKILL.md or prompt.md
result = await self._run_claude_code(full_prompt, task_id)
```

### Claude CLI Invocation
Agents run Claude CLI in headless mode with MCP tools:
```python
cmd = [
    "claude", "-p",  # Print mode (headless)
    "--output-format", "json",
    "--dangerously-skip-permissions",
    "--allowedTools", "Read,Edit,Bash,mcp__github,mcp__sentry,mcp__atlassian",
    "--append-system-prompt-file", str(prompt_file),
    "Execute the task..."
]
```

### Skill Loading
Skills are loaded from `skills/<name>/SKILL.md` or `skills/<name>/prompt.md`.

### Task Status Flow
`DISCOVERING` → `PENDING_APPROVAL` → `EXECUTING` → `COMPLETED` (or `FAILED`)

## Configuration

Key environment variables in `infrastructure/docker/.env`:
- `GITHUB_TOKEN` - Required for MCP GitHub operations
- `ANTHROPIC_API_KEY` - Optional if using OAuth (claude login)
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` - Jira integration
- `SENTRY_AUTH_TOKEN` - Sentry MCP access
- `SLACK_BOT_TOKEN` - Notifications

Settings loaded via Pydantic in `shared/config.py`.

## MCP Servers

Configured in `infrastructure/docker/mcp.json`:
- **github**: `ghcr.io/github/github-mcp-server` (Docker)
- **atlassian**: `https://mcp.atlassian.com/v1/mcp` (Remote)
- **sentry**: `@sentry/mcp-server@latest` (npx)
- **filesystem**: `@modelcontextprotocol/server-filesystem` (npx)

## Adding a New Skill

1. Create directory: `agents/<agent>/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter and instructions
3. Worker auto-discovers skills at runtime

## Code Style & Guidelines

1. **Package Management**:
   - ALWAY use `uv` for Python dependencies.
   - Dependencies are in `pyproject.toml`.
   - **NO** `requirements.txt` files allowed.
   - Dockerfiles use `uv pip install .`.

2. **Data Models**:
   - Use **Pydantic** models (v2) for all data structures (see `shared/models.py`).
   - Avoid raw dictionaries for complex data.

3. **Dashboard**:
   - Dashboard is a Go binary (`services/dashboard`).
   - Frontend is vanilla HTML/JS in `services/dashboard/static`.

4. **Testing**:
   - `pytest` for Python tests (Python 3.11+, line-length=100).
   - TDD validation is strictly enforced by the Executor Agent.
   - Use Ruff linter and mypy for type checking.

5. **Patterns**:
   - Async/await patterns throughout.
   - Structured logging via `shared/logging_utils.py`.

## 🐛 Troubleshooting

- **Streaming Limit Error**: Check `shared/claude_runner.py` for buffer limit handling.
- **Redis Error**: Verify `hset` vs `hmset` usage in `shared/task_queue.py`.
- **Webhook Issues**: Use `make tunnel` and check ngrok inspector.
- **Dependency Issues**: Run `make rebuild` to refresh `uv` environment in Docker.
