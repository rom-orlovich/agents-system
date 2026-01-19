# Claude Code CLI - Production Architecture

> **Enterprise AI Agent System powered by Claude Code CLI**
>
> Production-ready two-agent system with local-first development and cloud scalability

---

## 🎯 Overview

This system implements an enterprise-grade AI agent platform using **Claude Code CLI** as the foundation for autonomous bug fixing and code management. Unlike POC implementations, this is designed for production deployment with local development capabilities.

### Key Differentiators

| Aspect | This System | POC Version |
|--------|-------------|-------------|
| **Purpose** | Production deployment | Proof of concept |
| **Architecture** | Kubernetes-ready | Docker Compose only |
| **Scaling** | Auto-scaling workers | Fixed containers |
| **Infrastructure** | AWS EKS, RDS, ElastiCache | Local Docker |
| **Cost** | ~$1,100/month (5 seats) | ~$136/month |
| **Capacity** | 580 tasks/month (with approval) | 65 tasks/month |

---

## 🏗️ System Architecture

### Two-Agent Design Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLAUDE CODE CLI SYSTEM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐        ┌──────────────────────┐      │
│  │   PLANNING AGENT     │        │   EXECUTOR AGENT     │      │
│  │                      │        │                      │      │
│  │  • Discovery         │──Plan──▶│  • TDD Workflow     │      │
│  │  • Jira Enrichment   │        │  • Code Changes     │      │
│  │  • Plan Changes      │        │  • Testing          │      │
│  │  • Risk Assessment   │        │  • Git Operations   │      │
│  └──────────────────────┘        └──────────────────────┘      │
│           │                                  │                  │
│           └──────────────┬───────────────────┘                  │
│                          │                                      │
│                          ▼                                      │
│              ┌────────────────────────┐                         │
│              │   MCP SERVERS          │                         │
│              │  • GitHub              │                         │
│              │  • Atlassian (Jira)    │                         │
│              │  • Sentry              │                         │
│              │  • Filesystem          │                         │
│              └────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

#### Planning Agent

The Planning Agent (`agents/planning-agent/`) is responsible for:

| Skill | Purpose | MCP Tools Used |
|-------|---------|----------------|
| **Discovery** | Identify affected repositories and files | GitHub MCP (search_code, get_file_content) |
| **Jira Enrichment** | Enrich Sentry-created Jira tickets with analysis | Sentry MCP, GitHub MCP, Atlassian MCP |
| **Plan Changes** | Handle PR comment feedback | GitHub MCP |
| **Execution** | Execute approved fix plans | All MCPs |

#### Executor Agent

The Executor Agent (`agents/executor-agent/`) is responsible for:

| Skill | Purpose | Actions |
|-------|---------|---------|
| **Git Operations** | Clone, branch, commit, push | Full Git workflow |
| **TDD Workflow** | RED → GREEN → REFACTOR cycle | Test-first development |
| **Execution** | Implement fixes following plans | Code modification |
| **Code Review** | Self-review before commit | Quality checks |

---

## 🔄 Task Lifecycle

### Phase 1: Trigger
```
Sentry Alert → Jira Ticket Created (Sentry integration)
                    │
                    ▼
            Webhook Server (FastAPI)
                    │
                    ▼
            Redis: planning_queue
```

### Phase 2: Discovery & Planning
```
Planning Agent picks task
              │
    ┌─────────┼─────────┐
    │         │         │
    ▼         ▼         ▼
Discovery  Jira     Plan
  Skill   Enrich   Creating
              │
              ▼
        PLAN.md created
              │
              ▼
    Draft PR on GitHub
              │
              ▼
   Slack Notification
```

### Phase 3: Human Approval
```
GitHub Comment / Slack Button
              │
              ▼
       "@agent approve"
              │
              ▼
   Redis: execution_queue
```

### Phase 4: Execution
```
Executor Agent (any free worker)
              │
    ┌─────────┼─────────┐
    │         │         │
    ▼         ▼         ▼
  Setup    Write     Implement
   Git     Tests      Fix
 (clone)   (RED)    (GREEN)
              │
              ▼
      Verify Tests Pass
              │
              ▼
   Commit + Push to PR
              │
              ▼
    Update Jira + Slack
```

---

## 📂 Project Structure

```
claude-code-cli/
├── agents/
│   ├── planning-agent/
│   │   ├── Dockerfile              # Container definition
│   │   ├── worker.py               # Queue consumer & CLI invoker
│   │   ├── requirements.txt
│   │   └── skills/
│   │       ├── discovery/
│   │       │   └── SKILL.md        # Repo/file discovery
│   │       ├── execution/
│   │       │   └── SKILL.md        # Execute approved plans
│   │       ├── jira-enrichment/
│   │       │   ├── SKILL.md        # Enrich Jira tickets
│   │       │   └── prompt.md       # Detailed prompt
│   │       └── plan-changes/
│   │           └── SKILL.md        # Handle PR feedback
│   │
│   └── executor-agent/
│       ├── Dockerfile
│       ├── worker.py               # Queue consumer
│       ├── requirements.txt
│       └── skills/
│           ├── code-review/
│           │   └── SKILL.md        # Self-review checks
│           ├── execution/
│           │   └── SKILL.md        # Main orchestration
│           ├── git-operations/
│           │   └── SKILL.md        # Git workflow
│           └── tdd-workflow/
│               └── SKILL.md        # RED-GREEN-REFACTOR
│
├── services/
│   └── webhook-server/
│       ├── Dockerfile
│       ├── main.py                 # FastAPI application
│       ├── requirements.txt
│       └── routes/
│           ├── __init__.py
│           ├── github.py           # GitHub webhook handler
│           ├── jira.py             # Jira webhook handler
│           ├── sentry.py           # Sentry webhook handler
│           └── slack.py            # Slack webhook handler
│
├── shared/
│   ├── __init__.py
│   ├── enums.py                    # TokenStatus, TaskStatus, CommandType, Platform
│   ├── types.py                    # OAuthCredentials, Task, ParsedCommand
│   ├── constants.py                # BOT_CONFIG, QUEUE_CONFIG, TIMEOUT_CONFIG
│   ├── token_manager.py            # OAuth refresh + AWS Secrets sync
│   ├── git_utils.py                # Async git operations
│   ├── commands/                   # Bot command system
│   │   ├── definitions.yaml        # 17+ commands with aliases
│   │   ├── loader.py               # YAML to typed objects
│   │   ├── parser.py               # Message parsing
│   │   └── executor.py             # Command handlers
│   ├── config.py                   # Pydantic settings
│   ├── database.py                 # PostgreSQL connection
│   ├── github_client.py            # GitHub utilities (fallback)
│   ├── logging_utils.py            # Structured JSON logging
│   ├── metrics.py                  # Prometheus metrics
│   ├── models.py                   # Data models (Task, etc.)
│   ├── slack_client.py             # Slack notifications
│   └── task_queue.py               # Redis queue utilities
│
├── scripts/
│   ├── setup-skills.sh             # Install Claude Code skills (98% token savings!)
│   ├── setup-tunnel.sh             # Cloudflare Tunnel (FREE webhooks)
│   ├── refresh-token.py            # Cron token refresh
│   └── health-check.sh             # System health check
│
├── infrastructure/
│   └── docker/
│       ├── docker-compose.yml      # Local development
│       ├── mcp.json                # MCP servers configuration
│       ├── extract-oauth.sh        # Extract OAuth from Keychain
│       └── .env.example            # Environment template
│
├── tests/
│   └── test_commands.py            # Command parser tests
│
├── CLAUDE-CODE-CLI.ARCHITECTURE.md # This file
├── Makefile                        # Development commands
├── pyproject.toml                  # Python project config
└── README.md                       # User documentation
```

---

## 🛠️ Technology Stack

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Agent Runtime** | Claude Code CLI | Execute agent prompts with MCP tools |
| **Queue System** | Redis | Task distribution and coordination |
| **Database** | PostgreSQL | Task state and history |
| **API Server** | FastAPI | Webhook receiver |
| **Orchestration** | Docker Compose (local), Kubernetes (prod) | Container management |

### MCP Servers (Official)

| Server | Provider | Configuration | Tools Available |
|--------|----------|---------------|-----------------|
| **GitHub** | GitHub (Docker image) | `ghcr.io/github/github-mcp-server` | search_code, get_file_content, create_branch, create_pull_request, create_or_update_file, add_issue_comment |
| **Atlassian** | Atlassian (Remote) | `https://mcp.atlassian.com/v1/mcp` | get_issue, update_issue, add_comment, transition_issue, search_issues |
| **Sentry** | Sentry (npx) | `@sentry/mcp-server@latest` | get_sentry_issue, get_sentry_event, list_issues, resolve_issue |
| **Filesystem** | Anthropic (npx) | `@modelcontextprotocol/server-filesystem` | read_file, write_file, list_directory |

### MCP Configuration

Located at `infrastructure/docker/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "atlassian": {
      "url": "https://mcp.atlassian.com/v1/mcp"
    },
    "sentry": {
      "command": "npx",
      "args": ["-y", "@sentry/mcp-server@latest"],
      "env": {
        "SENTRY_ACCESS_TOKEN": "${SENTRY_AUTH_TOKEN}",
        "SENTRY_HOST": "${SENTRY_HOST:-sentry.io}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

### Infrastructure (Production)

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **Compute** | EKS (Kubernetes) | Run agent containers |
| **Database** | RDS PostgreSQL | Persistent storage |
| **Cache/Queue** | ElastiCache (Redis) | Task queuing |
| **Storage** | EFS | Shared workspace |
| **Load Balancer** | ALB | Traffic distribution |

---

## 🔧 Skills System

### Planning Agent Skills

#### 1. Discovery Skill
**Path**: `agents/planning-agent/skills/discovery/SKILL.md`

**Purpose**: Identify which repository contains the bug and which files are affected.

**Process**:
1. Parse error information (stack trace, error message)
2. Search GitHub for matching code using `github.search_code`
3. Identify repository and affected files
4. Find related test files

**Output**: JSON with repository, confidence score, affected files, root cause

#### 2. Jira Enrichment Skill
**Path**: `agents/planning-agent/skills/jira-enrichment/SKILL.md`

**Purpose**: Enrich Jira tickets created by Sentry with full analysis.

**Process**:
1. Fetch Sentry error details (stack trace, context)
2. Discover relevant files in GitHub
3. Analyze root cause
4. Update Jira ticket with analysis
5. Create GitHub draft PR with PLAN.md

**MCP Tools**: Sentry MCP, GitHub MCP, Atlassian MCP

#### 3. Plan Changes Skill
**Path**: `agents/planning-agent/skills/plan-changes/SKILL.md`

**Purpose**: Handle PR comment feedback and update plans.

**Process**:
1. Read developer feedback from PR comment
2. Update PLAN.md based on feedback
3. Commit changes and reply to comment

#### 4. Execution Skill
**Path**: `agents/planning-agent/skills/execution/SKILL.md`

**Purpose**: Execute approved fix plans.

**Process**:
1. Read approved PLAN.md
2. Implement code changes
3. Run tests
4. Commit and push

### Executor Agent Skills

#### 1. Git Operations Skill
**Path**: `agents/executor-agent/skills/git-operations/SKILL.md`

**Purpose**: Handle all Git operations.

**Operations**:
- Clone repository
- Create feature branch
- Commit changes
- Push to remote
- Update PR

**Convention**: Conventional Commits (`fix:`, `feat:`, `test:`, etc.)

#### 2. TDD Workflow Skill
**Path**: `agents/executor-agent/skills/tdd-workflow/SKILL.md`

**Purpose**: Execute RED → GREEN → REFACTOR cycle.

**Phases**:
1. **RED**: Write failing test that reproduces bug
2. **GREEN**: Implement minimal fix to pass test
3. **REFACTOR**: Clean up code (optional)

**Verification**: All tests must pass before commit

#### 3. Execution Skill
**Path**: `agents/executor-agent/skills/execution/SKILL.md`

**Purpose**: Main orchestration of execution.

**Steps**:
1. Read PLAN.md
2. Setup workspace (git-operations)
3. Execute each plan step
4. Run verification checks
5. Commit and push
6. Update Jira and Slack

#### 4. Code Review Skill
**Path**: `agents/executor-agent/skills/code-review/SKILL.md`

**Purpose**: Self-review before commit.

**Checks**:
- Code follows project patterns
- No linting errors
- No type errors
- Tests cover changes
- No security vulnerabilities

---

## 🌐 Deployment Models

### Local Development (Docker Compose)

```yaml
# docker-compose.yml services
services:
  redis:           # Queue - port 6379
  postgres:        # Database - port 5432
  webhook-server:  # API - port 8000
  planning-agent:  # Consumes planning_queue
  executor-agent:  # Consumes execution_queue
```

**Requirements**:
- Docker & Docker Compose
- Claude CLI authenticated (`claude login`)
- Environment variables in `.env`
- ngrok for webhook testing

**Cost**: $0 (uses local resources + Claude API)

### Production (AWS EKS)

```
Infrastructure:
├── 1 Planning Agent Pod (t3.large)
├── 2-8 Executor Agent Pods (t3.xlarge, auto-scaling)
├── 2 Webhook Server Pods
├── RDS PostgreSQL (db.t3.medium)
├── ElastiCache Redis (cache.t3.small)
└── EFS for shared workspace
```

**Monthly Cost**: ~$1,100
- Claude Teams: $750 (5 seats)
- AWS Infrastructure: $350

**Capacity**: ~580 tasks/month (with human approval bottleneck)

---

## 📊 Scaling Strategy

### Horizontal Scaling

| Component | Scaling Method | Metric |
|-----------|----------------|--------|
| Planning Agent | Manual (1-2 replicas) | Task latency |
| Executor Agent | HPA (2-8 replicas) | Queue length |
| Webhook Server | HPA (2-5 replicas) | CPU/Memory |

### Queue-Based Load Balancing

```
planning_queue → Planning Agent (1 instance)
       ↓
 execution_queue → Executor Agents (2-8 instances)
                   │
                   ├─ Worker 1 (idle)    ← picks task
                   ├─ Worker 2 (busy)
                   ├─ Worker 3 (idle)    ← picks task
                   └─ Worker 4 (busy)
```

**Auto-scaling Logic**:
- Scale up: Queue length > 2 tasks per worker
- Scale down: Queue empty for 5 minutes
- Min replicas: 2
- Max replicas: 8

---

## 🔐 Security

### Authentication & Authorization

| Service | Method |
|---------|--------|
| GitHub | Personal Access Token (read/write repo) |
| Jira | API Token (read/write issues) |
| Sentry | Auth Token (read issues) |
| Slack | Bot Token (post messages, read commands) |
| Claude API | Teams subscription (via CLI login) or API key |

### Secret Management

**Local**: `.env` file (gitignored)

**Production**: Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-agent-secrets
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "sk-ant-xxx"
  GITHUB_TOKEN: "ghp_xxx"
  JIRA_API_TOKEN: "xxx"
  SENTRY_AUTH_TOKEN: "xxx"
  SLACK_BOT_TOKEN: "xoxb-xxx"
```

### Webhook Validation

- **GitHub**: HMAC-SHA256 signature validation
- **Jira**: IP allowlist + signature
- **Sentry**: Secret token validation

---

## 📈 Monitoring & Observability

### Prometheus Metrics

Exposed at `/metrics` endpoint:

```python
# Exposed metrics
ai_agent_tasks_started_total{agent="planning|executor"}
ai_agent_tasks_completed_total{agent, status="success|failed"}
ai_agent_task_duration_seconds{agent, status}
ai_agent_queue_length{queue_name="planning_queue|execution_queue"}
ai_agent_errors_total{agent, error_type}
```

### Logging

**Structured JSON logs** (via `shared/logging_utils.py`):
```json
{
  "timestamp": "2026-01-19T10:30:00Z",
  "level": "INFO",
  "agent": "planning-agent",
  "task_id": "task-123",
  "message": "Discovery complete",
  "data": {
    "repository": "org/repo",
    "confidence": 0.95
  }
}
```

**Production**: Shipped to CloudWatch Logs

---

## 💰 ROI Analysis

### Cost Breakdown (50 Developers, 5 Seats)

| Item | Monthly Cost |
|------|--------------|
| Claude Teams (5 seats) | $750 |
| AWS EKS + EC2 | $250 |
| RDS + ElastiCache | $80 |
| ALB + misc | $20 |
| **Total** | **$1,100** |

### Capacity (With Human Approval)

| Metric | Value |
|--------|-------|
| Pure agent capacity | 1,320 tasks/month |
| With human approval (~2.5h/task) | **580 tasks/month** |
| Bottleneck | Human approval (56% idle) |

### Value Delivered

**Based on Industry Benchmarks (SWE-bench)**:
- Claude Code success rate: **75%**
- Tasks completed: 580 × 75% = **435/month**
- Time saved per task: 2 hours
- Hours saved: 435 × 2h = **870 hours**
- Developer cost: $60/hour
- **Monthly savings**: 870 × $60 = **$52,200**

**ROI Calculation**:
- Net value: $52,200 - $1,100 = **$51,100/month**
- ROI: **4,645%**
- Payback: < 1 day

---

## 🚀 Getting Started

### Prerequisites

```bash
# Required tools
- Docker 20+
- Docker Compose 2+
- Node.js 20+ (for MCP servers)
- Python 3.11+
- Claude CLI

# Required accounts
- Claude Teams subscription OR ANTHROPIC_API_KEY
- GitHub account with PAT
- Jira account with API token
- Sentry account (optional)
- Slack workspace (optional)
```

### Local Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/agents-system.git
cd agents-system/claude-code-cli

# 2. Install Claude CLI
npm install -g @anthropic-ai/claude-code

# 3. Authenticate Claude
claude login

# 4. Configure environment
cp infrastructure/docker/.env.example infrastructure/docker/.env
# Edit .env with your credentials

# 5. Build images
cd infrastructure/docker
docker-compose build

# 6. Start system
docker-compose up -d

# 7. Verify health
curl http://localhost:8000/health

# 8. Expose Webhooks (in separate terminal)
ngrok http 8000
```

---

## 🎯 Best Practices

### Skill Design

1. **Single responsibility** - one skill, one purpose
2. **Clear inputs/outputs** - documented JSON schemas
3. **Error handling** - graceful degradation
4. **Idempotency** - safe to retry
5. **Logging** - track execution steps

### Queue Management

1. **Task priorities** - critical bugs first
2. **Retry logic** - exponential backoff
3. **Dead letter queue** - failed tasks
4. **TTL** - prevent stale tasks
5. **Monitoring** - queue length alerts

---

## 🔮 Future Enhancements

### Phase 2: Advanced Features

- [ ] Multi-repository fixes (refactoring across services)
- [ ] Automatic rollback on failing tests
- [ ] Cost optimization suggestions
- [ ] Security vulnerability scanning
- [ ] Performance profiling integration

### Phase 3: Intelligence Improvements

- [ ] Learning from past fixes (RAG)
- [ ] Custom models fine-tuned on codebase
- [ ] Predictive bug detection
- [ ] Code quality scoring
- [ ] Technical debt tracking

### Phase 4: Enterprise Features

- [ ] Multi-tenant support
- [ ] RBAC and audit logs
- [ ] SLA monitoring and reporting
- [ ] Batch processing for large backlogs
- [ ] Integration with more tools (Linear, GitLab, etc.)

---

## 📚 Additional Resources

- [Official Claude Code CLI Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Sentry MCP Server](https://docs.sentry.io/product/integrations/integration-platform/mcp/)
- [Atlassian MCP](https://mcp.atlassian.com)

---

## 📞 Support

For questions or issues:
1. Check the documentation
2. Review GitHub Issues
3. Contact the team via Slack #ai-agents

---

**Last Updated**: January 2026  
**Version**: 1.0.0  
**Status**: Production Ready
