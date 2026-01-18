# Claude Code CLI POC - Architecture & Implementation

> **Two-Agent System for Automated Bug Fixing Using Claude Code CLI**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [MCP Integration](#mcp-integration)
5. [Slack Integration](#slack-integration)
6. [Cost Analysis](#cost-analysis)
7. [Capacity & Performance](#capacity--performance)
8. [Feasibility Analysis](#feasibility-analysis)
9. [Deployment](#deployment)

---

## Overview

### What is This System?

A **Dockerized two-agent system** using Claude Code CLI for autonomous software development:

```
Jira/Sentry Webhook → Planning Agent → Draft PR → Human Approval → Executor Agent → Code + Tests + PR
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Two Specialized Agents** | Planning (discovery + plan) + Executor (TDD implementation) |
| **Official MCP Servers** | GitHub, Atlassian (Jira), Sentry |
| **Slack Integration** | Trigger actions + receive notifications |
| **Human-in-the-Loop** | PR approval required before code execution |
| **Full Docker Setup** | Ready for EC2 deployment |

### Agent Roles

```mermaid
graph LR
    subgraph Triggers
        J[Jira Ticket]
        S[Sentry Alert]
        SL[Slack Command]
    end
    
    subgraph Planning["Planning Agent"]
        D[Discovery]
        P[Create Plan]
        PR1[Draft PR]
    end
    
    subgraph Approval
        H[Human Review]
    end
    
    subgraph Executor["Executor Agent"]
        T[Write Tests]
        I[Implement]
        PR2[Update PR]
    end
    
    J --> D
    S --> D
    SL --> D
    D --> P --> PR1 --> H
    H -->|@agent approve| T --> I --> PR2
```

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              EC2 Instance                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐  │
│  │  Webhook Server │     │  Planning Agent  │     │ Executor Agent  │  │
│  │    (FastAPI)    │────▶│   Claude CLI     │     │   Claude CLI    │  │
│  │      :8000      │     │                  │     │                 │  │
│  └────────┬────────┘     └────────┬─────────┘     └────────┬────────┘  │
│           │                       │                        │           │
│           ▼                       ▼                        ▼           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          Redis Queue                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Shared Volume (/workspace)                    │   │
│  │                    ~/.claude (mounted from host)                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  GitHub  │        │   Jira   │        │  Sentry  │
    │ (MCP)    │        │  (MCP)   │        │  (MCP)   │
    └──────────┘        └──────────┘        └──────────┘
```

### Directory Structure

```
claude-code-cli-poc/
├── .claude/
│   └── mcp.json                 # MCP servers configuration
│
├── webhook-server/              # FastAPI webhook receiver
│   ├── Dockerfile
│   ├── main.py                  # FastAPI app
│   ├── queue.py                 # Redis queue
│   └── routes/
│       ├── jira.py              # Jira webhook handler
│       ├── sentry.py            # Sentry webhook handler
│       └── github.py            # GitHub PR approval handler
│
├── planning-agent/              # Planning & Discovery Agent
│   ├── Dockerfile
│   ├── CLAUDE.md                # Claude CLI instructions
│   ├── worker.py                # Redis queue worker
│   └── .claude/skills/          # Agent skills
│       ├── discovery/SKILL.md
│       ├── planning/SKILL.md
│       ├── sentry-analysis/SKILL.md
│       └── slack-notifications/SKILL.md
│
├── executor-agent/              # Executor Agent
│   ├── Dockerfile
│   ├── CLAUDE.md                # Claude CLI instructions
│   ├── worker.py                # Redis queue worker
│   └── .claude/skills/
│       └── execution/SKILL.md
│
├── shared/                      # Shared utilities
│   ├── config.py                # Pydantic settings
│   ├── slack_bot.py             # Slack SDK integration
│   ├── jira_client.py
│   └── github_client.py
│
├── scripts/
│   ├── setup-machine.sh         # EC2 setup script
│   ├── deploy.sh                # Deployment script
│   └── run-pipeline.sh          # Manual trigger
│
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Components

### 1. Webhook Server

**Purpose:** Receives webhooks and routes to appropriate agent queues.

| Endpoint | Trigger | Target |
|----------|---------|--------|
| `POST /jira-webhook` | Jira ticket with AI-Fix label | Planning Agent |
| `POST /sentry-webhook` | Sentry error alert | Planning Agent |
| `POST /github-webhook` | PR comment `@agent approve` | Executor Agent |
| `GET /health` | Health check | - |

### 2. Planning Agent

**Purpose:** Discover code, create TDD plan, open Draft PR.

**Skills:**
- `discovery` - Find relevant repos and files
- `planning` - Create PLAN.md with TDD tasks
- `sentry-analysis` - Analyze Sentry errors
- `slack-notifications` - Send Slack updates

**Process Flow:**
```
1. Receive task from Redis queue
2. Read ticket/error details
3. Search GitHub for relevant code
4. Create PLAN.md with TDD tasks
5. Create feature branch + Draft PR
6. Notify Slack for approval
```

### 3. Executor Agent

**Purpose:** Implement code following approved PLAN.md.

**Skills:**
- `execution` - TDD implementation

**Process Flow:**
```
1. Receive approved task from Redis queue
2. Clone repo, checkout branch
3. Read PLAN.md
4. For each task:
   - Write tests (red)
   - Implement code (green)
   - Run tests
   - Commit
5. Push changes
6. Update PR (remove draft)
7. Notify Slack completion
```

---

## MCP Integration

### Official MCP Servers

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server"]
    },
    "atlassian": {
      "url": "https://mcp.atlassian.com/v1/mcp"
    },
    "sentry": {
      "command": "npx",
      "args": ["-y", "@sentry/mcp-server@latest"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

### MCP Tools Available

| MCP Server | Key Tools |
|------------|-----------|
| **GitHub** | `search_code`, `get_file_content`, `create_pull_request`, `create_branch` |
| **Atlassian** | `get_issue`, `add_comment`, `create_issue`, `transition_issue` |
| **Sentry** | `list_issues`, `get_issue_events`, `resolve_issue` |
| **Filesystem** | `read_file`, `write_file`, `list_directory` |

---

## Slack Integration

### Overview

Slack provides **bidirectional communication**:
- **Inbound:** Users trigger actions via commands
- **Outbound:** System sends notifications and updates

### Slack Commands (Inbound)

| Command | Action |
|---------|--------|
| `/agent status <ticket>` | Get task status |
| `/agent approve <ticket>` | Approve plan for execution |
| `/agent reject <ticket>` | Reject plan |
| `/agent retry <ticket>` | Retry failed task |
| `/agent run <ticket>` | Manually trigger planning |

### Notifications (Outbound)

| Event | Notification |
|-------|--------------|
| Plan Ready | "📋 Plan ready for PROJ-123 - [View PR]" with Approve/Reject buttons |
| Execution Started | "⚙️ Executing plan for PROJ-123..." |
| Tests Passed | "✅ All 15 tests passed for PROJ-123" |
| Tests Failed | "❌ 3 tests failed for PROJ-123 - [View Logs]" |
| PR Ready | "🎉 PR ready for review: PROJ-123" |
| Error | "🚨 Agent error: <details>" |

### Interactive Buttons

```
┌──────────────────────────────────────────────────────────┐
│ 📋 Plan Ready for Review: PROJ-123                       │
│                                                          │
│ Summary: Add OAuth authentication flow                   │
│ Branch: feature/proj-123-oauth                           │
│ Tasks: 4 (est. 8 hours)                                  │
│                                                          │
│  [📄 View PR]  [✅ Approve]  [❌ Reject]                  │
└──────────────────────────────────────────────────────────┘
```

---

## Cost Analysis

### Monthly Cost Breakdown

| Component | Specification | Cost/Month |
|-----------|---------------|------------|
| **Claude Teams** | 1 seat | $150 |
| **EC2 Instance** | t3.medium (2 vCPU, 4GB) | ~$30 |
| **EBS Storage** | 50GB gp3 | ~$5 |
| **Redis** | Docker container (included) | $0 |
| **Data Transfer** | ~10GB | ~$1 |
| **Total Fixed** | | **~$186/month** |

### Variable Costs (Claude API Usage)

| Metric | Estimate |
|--------|----------|
| Avg tokens per task | ~50,000 tokens |
| Claude Sonnet price | $3/1M input, $15/1M output |
| Cost per task | ~$0.50 - $2.00 |

### Total Cost Estimates

| Usage Level | Tasks/Month | Monthly Cost |
|-------------|-------------|--------------|
| **Light** | 20 tasks | ~$200 |
| **Medium** | 50 tasks | ~$250 |
| **Heavy** | 100 tasks | ~$350 |

> **Note:** Claude Teams at $150/month includes generous rate limits suitable for automated agent usage.

---

## Capacity & Performance

### Task Processing Capacity

| Metric | Estimate |
|--------|----------|
| **Planning Agent** | ~10-20 minutes per task |
| **Executor Agent** | ~20-60 minutes per task |
| **Total Task Time** | ~30-80 minutes end-to-end |
| **Parallel Tasks** | 1 (sequential queue) |

### Monthly Capacity (Single Instance)

| Work Pattern | Tasks/Day | Tasks/Month |
|--------------|-----------|-------------|
| **8h workday** | 6-12 tasks | 120-240 tasks |
| **24/7 operation** | 18-36 tasks | 540-1080 tasks |
| **Realistic (with failures)** | 4-8 tasks | 80-160 tasks |

### Task Complexity Guidelines

| Complexity | Description | Est. Time |
|------------|-------------|-----------|
| **Simple** | Single file fix, clear error | 30 min |
| **Medium** | 2-5 files, tests needed | 60 min |
| **Complex** | Multiple repos, architecture change | 90+ min |

---

## Feasibility Analysis

### ✅ What This System CAN Do

| Capability | Details |
|------------|---------|
| **Simple Bug Fixes** | Clear error → fix → test |
| **Sentry Error Resolution** | Stack trace → locate → fix |
| **Test Writing** | Add tests for existing code |
| **Code Refactoring** | Improve code following patterns |
| **Documentation** | Update docs with code changes |
| **Linting Fixes** | Auto-fix ESLint, Prettier, Ruff |

### ⚠️ What Requires Human Oversight

| Scenario | Why |
|----------|-----|
| **Architecture Changes** | Needs design review |
| **Security-Related Fixes** | Needs security review |
| **Breaking API Changes** | Needs impact assessment |
| **Complex Cross-Repo** | May miss dependencies |

### ❌ What This System CANNOT Do

| Limitation | Reason |
|------------|--------|
| **UI/UX Changes** | Cannot visually verify |
| **Performance Optimization** | Cannot benchmark |
| **Business Logic Decisions** | Needs domain expertise |
| **Production Deployment** | Safety concern |

### Success Rate Expectations

| Task Type | Expected Success Rate |
|-----------|----------------------|
| Lint/Format fixes | 95%+ |
| Simple bug fixes | 70-80% |
| Feature implementation | 50-70% |
| Complex refactoring | 30-50% |

### ROI Analysis

| Factor | Calculation |
|--------|-------------|
| **Developer hourly cost** | ~$75/hour |
| **Time saved per task** | 1-4 hours |
| **Value per task** | $75-$300 |
| **System cost per task** | $2-5 |
| **ROI per task** | 15x - 150x |

**Break-even:** ~3-5 successful tasks per month covers system cost.

---

## Deployment

### Quick Start

```bash
# 1. Clone and configure
cd claude-code-cli-poc
cp .env.example .env
# Edit .env with credentials

# 2. Authenticate Claude CLI (on host)
claude login

# 3. Build and run
docker-compose build
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

### EC2 Deployment

```bash
# On your machine
./scripts/deploy.sh ubuntu@your-ec2-host.amazonaws.com
```

### Webhook Configuration

| Service | Webhook URL |
|---------|-------------|
| Jira | `https://your-server/jira-webhook` |
| Sentry | `https://your-server/sentry-webhook` |
| GitHub | `https://your-server/github-webhook` |

### Environment Variables

```bash
# Claude
CLAUDE_CONFIG_DIR=/root/.claude

# GitHub
GITHUB_TOKEN=ghp_xxx

# Jira (for webhook validation)
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=xxx

# Sentry
SENTRY_AUTH_TOKEN=xxx
SENTRY_ORG=your-org

# Slack
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_AGENTS=#ai-agents
SLACK_CHANNEL_ERRORS=#ai-errors

# Redis
REDIS_URL=redis://redis:6379/0
```

---

## Summary

### System Strengths

- ✅ Uses official MCP servers (GitHub, Atlassian, Sentry)
- ✅ Human-in-the-loop approval before code execution
- ✅ TDD methodology ensures test coverage
- ✅ Slack integration for control and visibility
- ✅ Fully Dockerized for easy deployment
- ✅ Low cost (~$200/month for light usage)

### Recommended Use Cases

1. **Sentry Error Triage** - Automatically analyze and propose fixes
2. **Simple Bug Fixes** - Issues with clear reproduction steps
3. **Test Coverage** - Add tests for existing code
4. **Code Quality** - Fix linting, formatting, small refactors

### Getting Started

1. Deploy to EC2 or local Docker
2. Configure webhooks in Jira/Sentry/GitHub
3. Add Slack bot to workspace
4. Create first Jira ticket with `AI-Fix` label
5. Review Draft PR and approve via Slack or PR comment
