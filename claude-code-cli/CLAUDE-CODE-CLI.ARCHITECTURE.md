# Claude Code CLI - System Architecture

> **AI Agent System for Autonomous Bug Fixing**

Production-ready two-agent system using Claude Code CLI with MCP integrations for automated bug analysis and fixes.

---

## 🎯 Overview

This system uses **Claude Code CLI** with **Model Context Protocol (MCP)** to autonomously fix bugs through a two-agent workflow:

1. **Planning Agent** - Analyzes bugs and creates fix plans
2. **Executor Agent** - Implements fixes using TDD workflow

---

## 🏗️ Architecture

```
Webhooks → Webhook Server → Redis Queue → Agents → MCP Tools
(Sentry/    (FastAPI)      (planning/     (Claude   (GitHub/
 Jira/                      execution)      Code)    Jira/
 GitHub)                                      ↓      Sentry)
                                          Dashboard
                                          (Go/HTML)
```

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Planning Agent** | Claude Code CLI + Python | Analyzes bugs, creates fix plans |
| **Executor Agent** | Claude Code CLI + Python | Implements fixes with TDD |
| **Webhook Server** | FastAPI | Receives webhooks from external services |
| **Dashboard**      | Go + HTML/JS | Real-time task tracking and session metrics |
| **Redis Queue** | Redis | Task distribution and coordination |
| **MCP Servers** | Official MCP implementations | Tool access (GitHub, Jira, Sentry, Filesystem) |

---

## 🔄 Task Lifecycle

### 1. Trigger
```
Sentry Alert → Jira Ticket → Webhook Server → Redis (planning_queue)
```

### 2. Planning
```
Planning Agent:
  ├─ Fetch Sentry error details
  ├─ Discover affected code in GitHub
  ├─ Analyze root cause
  ├─ Create PLAN.md (TDD approach)
  └─ Open draft PR + notify Slack
```

### 3. Approval
```
Human reviews PLAN.md → @agent approve → Redis (execution_queue)
```

### 4. Execution
```
Executor Agent:
  ├─ Clone repo + create branch
  ├─ Write failing tests (RED)
  ├─ Implement fix (GREEN)
  ├─ Run all tests
  ├─ Commit + push to PR
  └─ Update Jira + Slack
```

---

## 📂 Project Structure

```
claude-code-cli/
├── agents/
│   ├── planning-agent/          # Analyzes bugs, creates plans
│   │   ├── worker.py            # Queue consumer + Claude CLI invoker
│   │   └── skills/              # Planning skills (SKILL.md files)
│   │       ├── discovery/       # Find affected repos/files
│   │       ├── jira-enrichment/ # Enrich Jira tickets
│   │       ├── plan-changes/    # Handle PR feedback
│   │       └── execution/       # Execute approved plans
│   │
│   └── executor-agent/          # Implements fixes
│       ├── worker.py            # TDD workflow executor
│       └── skills/              # Execution skills
│           ├── git-operations/  # Git workflow
│           ├── tdd-workflow/    # RED-GREEN-REFACTOR
│           ├── execution/       # Main orchestration
│           └── code-review/     # Self-review checks
│
├── services/webhook-server/     # FastAPI webhook receiver
│   ├── main.py
│   └── routes/                  # GitHub, Jira, Slack, Sentry
│
├── shared/                      # Shared utilities
│   ├── models.py                # Pydantic task models
│   ├── task_queue.py            # Redis queue operations
│   ├── commands/                # Bot command system
│   ├── claude_runner.py         # Claude CLI wrapper
│   └── ...                      # Config, logging, metrics
│
└── infrastructure/docker/
    ├── docker-compose.yml       # Local development
    ├── mcp.json                 # MCP server configuration
    └── extract-oauth.sh         # OAuth credential extraction
```

---

## 🔧 MCP Configuration

MCP servers provide tool access to agents. Configuration in `infrastructure/docker/mcp.json`:

| Server | Provider | Tools |
|--------|----------|-------|
| **GitHub** | GitHub (Docker) | search_code, create_pr, add_comment, get_file_content |
| **Atlassian** | Atlassian (Remote) | get_issue, update_issue, add_comment, transition_issue |
| **Sentry** | Sentry (npx) | get_sentry_issue, get_sentry_event, list_issues |
| **Filesystem** | Anthropic (npx) | read_file, write_file, list_directory |

### Example Configuration

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", 
               "-e", "GITHUB_TOOLSETS=default,actions,code_security",
               "ghcr.io/github/github-mcp-server"]
    },
    "atlassian": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://mcp.atlassian.com/v1/sse"]
    }
  }
}
```

**GitHub Toolsets**:
- `default` - Core operations (search, PR, comments)
- `actions` - CI/CD monitoring (workflow runs, logs, retry)
- `code_security` - Security scanning

---

## 🎯 Skills System

Skills are modular instructions for agents, defined in `SKILL.md` files with YAML frontmatter.

### Planning Agent Skills

| Skill | Purpose | MCP Tools |
|-------|---------|-----------|
| **discovery** | Find affected repos and files | GitHub (search_code) |
| **jira-enrichment** | Enrich Jira tickets with analysis | Sentry, GitHub, Atlassian |
| **plan-changes** | Update plans based on feedback | GitHub (get_pr, add_comment) |
| **execution** | Execute approved fix plans | All MCPs |

### Executor Agent Skills

| Skill | Purpose | Actions |
|-------|---------|---------|
| **git-operations** | Git workflow (clone, branch, commit, push) | Git commands |
| **tdd-workflow** | RED → GREEN → REFACTOR cycle | Test execution |
| **execution** | Main orchestration | Coordinates all skills |
| **code-review** | Self-review before commit | Linting, type checking |

### Skill Format

```markdown
---
name: skill-name
description: What this skill does
---

# Skill Name

## Purpose
Clear description

## When to Use
Trigger conditions

## MCP Tools
- github.search_code
- jira.get_issue

## Process
1. Step 1
2. Step 2

## Output
Expected output format
```

---

## 🔐 Security

**Authentication**:
- GitHub: Personal Access Token (repo read/write)
- Jira: API Token (issue read/write)
- Sentry: Auth Token (issue read)
- Slack: Bot Token (post messages)
- Claude: OAuth (subscription) or API key

**Secrets**: Stored in `.env` file (gitignored)

**Webhook Validation**:
- GitHub: HMAC-SHA256 signature
- Jira: Secret token + IP allowlist
- Sentry: Secret token

---

## 📊 Monitoring

**Prometheus Metrics** (`/metrics` endpoint):
```
ai_agent_tasks_started_total{agent="planning|executor"}
ai_agent_tasks_completed_total{agent, status="success|failed"}
ai_agent_task_duration_seconds{agent, status}
ai_agent_queue_length{queue_name}
ai_agent_errors_total{agent, error_type}
```

**Structured Logging** (JSON):
```json
{
  "timestamp": "2026-01-20T10:30:00Z",
  "level": "INFO",
  "agent": "planning-agent",
  "task_id": "task-123",
  "message": "Discovery complete",
  "data": {"repository": "org/repo", "confidence": 0.95}
}
```

---

## 🚀 Deployment

### Local Development (Docker Compose)

```yaml
services:
  redis:           # Queue (port 6379)
  webhook-server:  # API (port 8000)
  planning-agent:  # Consumes planning_queue
  executor-agent:  # Consumes execution_queue
```

**Requirements**:
- Docker & Docker Compose
- Claude CLI authenticated (`claude login`)
- Environment variables in `.env`
- ngrok for webhook testing

### Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| Claude Teams (5 seats) | $750 |
| AWS Infrastructure (prod) | $350 |
| **Total** | **~$1,100/mo** |

### ROI Summary

| Metric | Value |
|--------|-------|
| Tasks/Month | ~580 |
| Success Rate | 75% |
| Hours Saved/Month | 812 |
| Engineer Cost ($60/hr) | $48,720 |
| **ROI** | **~4,300%** |

> **Note**: Local development costs $0 (just Claude subscription). ROI assumes production deployment with AWS.

---

## 🎓 Best Practices

### Skill Design
1. **Single responsibility** - One skill, one purpose
2. **Clear inputs/outputs** - Documented schemas
3. **Error handling** - Graceful degradation
4. **Idempotency** - Safe to retry

### Queue Management
1. **Task priorities** - Critical bugs first
2. **Retry logic** - Exponential backoff
3. **Dead letter queue** - Failed tasks
4. **TTL** - Prevent stale tasks

---

## 📚 Resources

- [Claude Code CLI Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [MCP Protocol](https://modelcontextprotocol.io)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Sentry MCP Server](https://docs.sentry.io/product/integrations/integration-platform/mcp/)
- [Atlassian MCP](https://mcp.atlassian.com)

---

**Last Updated**: January 2026  
**Version**: 1.1.0  
**Status**: Production Ready
