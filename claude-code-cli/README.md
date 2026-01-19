# 🤖 Claude Code CLI - Production AI Agent System

> **Enterprise-grade autonomous bug fixing powered by Claude Code CLI**

A production-ready implementation of a two-agent system (Planning + Executor) that autonomously fixes bugs, writes tests, and creates pull requests - built on Claude Code CLI and designed to scale from local development to cloud deployment.

---

## ✨ What Makes This Different?

Unlike the POC version (`claude-code-cli-poc/`), this system is designed for **production deployment**:

| Feature | This System | POC Version |
|---------|-------------|-------------|
| **Target** | Production (50+ devs) | Local testing |
| **Scaling** | Auto-scaling workers | Fixed containers |
| **Infrastructure** | Kubernetes + AWS | Docker Compose only |
| **Capacity** | 580 tasks/month | 65 tasks/month |
| **Cost** | ~$1,100/month | ~$136/month |
| **ROI** | 4,329% (50 devs) | Proof of value |

---

## 🎯 Quick Overview

This system automates the entire bug-fixing workflow:

```
1. Sentry Alert → 2. Planning Agent → 3. Human Approval → 4. Executor Agent → 5. PR Created
   (Error)          (Analyze + Plan)    (@agent approve)   (Fix + Test)       (Ready!)
```

### What It Does

✅ **Analyzes** error reports from Sentry  
✅ **Identifies** affected repositories and files  
✅ **Plans** TDD-based fixes (tests first!)  
✅ **Waits** for human approval  
✅ **Implements** fixes following the plan  
✅ **Runs** all tests to verify  
✅ **Creates** pull requests ready for review  
✅ **Updates** Jira tickets and Slack notifications  

---

## 🏗️ Architecture

### Two-Agent Design

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  📊 TRIGGERS                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Sentry  │  │  Jira   │  │  Slack  │  │Dashboard│           │
│  │ Webhook │  │ Webhook │  │ Command │  │   UI    │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       └────────────┴────────────┴─────────────┘                │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                            │
│              │  Webhook Server     │                            │
│              │  (FastAPI)          │                            │
│              └──────────┬──────────┘                            │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                            │
│              │  Redis Queue        │                            │
│              │  • planning_queue   │                            │
│              │  • execution_queue  │                            │
│              └──────────┬──────────┘                            │
│                         │                                       │
│       ┌─────────────────┴─────────────────┐                    │
│       │                                   │                    │
│       ▼                                   ▼                    │
│  ┌─────────────────┐             ┌─────────────────┐          │
│  │ Planning Agent  │             │ Executor Agent  │          │
│  │                 │             │  (Auto-scaling) │          │
│  │ • Discovery     │──Plan.md──▶ │ • TDD Workflow  │          │
│  │ • Analysis      │             │ • Git Ops       │          │
│  │ • Planning      │             │ • Testing       │          │
│  └────────┬────────┘             └────────┬────────┘          │
│           │                               │                    │
│           └───────────┬───────────────────┘                    │
│                       │                                        │
│                       ▼                                        │
│            ┌────────────────────┐                              │
│            │   MCP Servers      │                              │
│            │  • GitHub          │                              │
│            │  • Atlassian/Jira  │                              │
│            │  • Sentry          │                              │
│            │  • Filesystem      │                              │
│            └────────────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Technology |
|-----------|---------|-----------:|
| **Planning Agent** | Analyzes bugs, creates execution plans | Claude Code CLI + MCP |
| **Executor Agent** | Implements fixes following TDD | Claude Code CLI + MCP |
| **Webhook Server** | Receives triggers from external services | FastAPI |
| **Queue System** | Distributes tasks between agents | Redis |
| **Database** | Stores task state and history | PostgreSQL |

---

## 📂 Project Structure

```
claude-code-cli/
├── agents/
│   ├── planning-agent/
│   │   ├── Dockerfile
│   │   ├── worker.py               # Queue consumer & Claude CLI invoker
│   │   ├── requirements.txt
│   │   └── skills/
│   │       ├── discovery/SKILL.md
│   │       ├── execution/SKILL.md
│   │       ├── jira-enrichment/
│   │       └── plan-changes/SKILL.md
│   │
│   └── executor-agent/
│       ├── Dockerfile
│       ├── worker.py               # TDD workflow executor
│       ├── requirements.txt
│       └── skills/
│           ├── code-review/SKILL.md
│           ├── git-operations/SKILL.md
│           └── tdd-workflow/SKILL.md
│
├── services/
│   └── webhook-server/
│       ├── Dockerfile
│       ├── main.py                 # FastAPI app
│       ├── requirements.txt
│       └── routes/
│           ├── github.py           # Supports @agent commands
│           ├── jira.py
│           └── slack.py
│
├── shared/
│   ├── enums.py                    # TokenStatus, TaskStatus, CommandType
│   ├── types.py                    # OAuthCredentials, Task, ParsedCommand
│   ├── constants.py                # BOT_CONFIG, QUEUE_CONFIG
│   ├── token_manager.py            # OAuth refresh + AWS sync
│   ├── git_utils.py                # Async git operations
│   ├── commands/                   # Bot command system
│   │   ├── definitions.yaml        # All 17 commands
│   │   ├── loader.py
│   │   ├── parser.py
│   │   └── executor.py
│   ├── config.py
│   ├── database.py
│   ├── github_client.py
│   ├── logging_utils.py
│   ├── metrics.py
│   ├── models.py
│   ├── slack_client.py
│   └── task_queue.py
│
├── scripts/
│   ├── setup-skills.sh             # Install Claude Code skills
│   ├── setup-tunnel.sh             # Cloudflare Tunnel (FREE!)
│   ├── refresh-token.py            # Cron token refresh
│   └── health-check.sh
│
├── infrastructure/
│   └── docker/
│       ├── docker-compose.yml
│       ├── mcp.json                # MCP servers config
│       ├── extract-oauth.sh
│       └── .env.example
│
├── tests/
│   └── test_commands.py
│
├── Makefile
├── pyproject.toml
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have:

- ✅ Docker 20+ and Docker Compose 2+
- ✅ Node.js 20+ (for MCP servers)
- ✅ Claude Pro/Teams subscription **OR** ANTHROPIC_API_KEY
- ✅ GitHub Personal Access Token
- ✅ Jira API Token (optional)
- ✅ Sentry Auth Token (optional)

### 1. Install Claude CLI

```bash
# Install globally
npm install -g @anthropic-ai/claude-code

# Authenticate (required for agents to work)
claude login
```

### 2. Configure Authentication

You have two options for authenticating Claude Code CLI in Docker:

#### Option A: OAuth (Recommended - Use Your Subscription)

If you have a Claude Pro or Teams subscription, you can use OAuth credentials:

```bash
# Login on your host machine (one-time)
claude login

# The credentials are automatically mounted into Docker containers
# See infrastructure/docker/OAUTH-SETUP.md for details
```

> **See [OAUTH-SETUP.md](./infrastructure/docker/OAUTH-SETUP.md)** for detailed OAuth configuration, including cloud deployment with multiple machines.

#### Option B: API Key

If you prefer using an API key from console.anthropic.com:

```bash
# Add to infrastructure/docker/.env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### 3. Configure Environment

```bash
# Copy example environment file
cp infrastructure/docker/.env.example infrastructure/docker/.env

# Edit with your credentials
nano infrastructure/docker/.env
```

Required variables:
```bash
# Anthropic (optional if using OAuth)
ANTHROPIC_API_KEY=sk-ant-xxx

# GitHub (required)
GITHUB_TOKEN=ghp_your_token_here

# Jira (optional)
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your_token

# Sentry (optional)
SENTRY_AUTH_TOKEN=your_token
SENTRY_HOST=sentry.io

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_AGENTS=#ai-agents
```

### 3. Build and Start

```bash
# From project root
cd infrastructure/docker

# Build all images
docker-compose build

# Start all services
docker-compose up -d

# Check service health (~30 seconds to be ready)
docker-compose ps
```

### 4. Expose to Internet (Cloudflare Tunnel - FREE!)

For GitHub/Jira/Sentry to send webhooks to your local machine:

```bash
# One-time setup
make tunnel

# Or run directly
./scripts/setup-tunnel.sh
```

This creates a **free, permanent URL** for your webhooks (e.g., `https://agents.yourdomain.com`).

> **Why Cloudflare Tunnel instead of ngrok?**
> - ✅ FREE (no paid subscription)
> - ✅ Custom domain support
> - ✅ Never-changing URL
> - ✅ Built-in DDoS protection

### 5. Verify Installation

```bash
# Check service health
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"webhook-server"}

# Full health check
make health
```

---

## 📖 Usage

### Triggering Tasks

#### Via Jira Webhook (Automatic)

When Sentry creates a Jira ticket (via Sentry-Jira integration), the system automatically:
1. Receives the Jira webhook
2. Enriches the ticket with error analysis
3. Creates a draft PR with fix plan

#### Via GitHub Comment

Comment on any PR with `@agent approve` to trigger the execution phase.

#### Via Slack (If configured)

```bash
/agent run Fix null pointer exception in authentication service
```

### Monitoring Tasks

#### Logs

```bash
# View all logs
docker-compose logs -f

# Planning agent only
docker-compose logs -f planning-agent

# Executor agent only
docker-compose logs -f executor-agent

# Webhook server
docker-compose logs -f webhook-server
```

### Approving Plans

After the Planning Agent creates a plan, you'll receive notifications via:

1. **GitHub**: Draft PR with PLAN.md
2. **Slack**: Message with "Approve" button (if configured)

**To approve**:

**GitHub**: Comment `@agent approve` on the PR

**Slack**: Click the "✅ Approve" button or type `@agent approve`

### Bot Commands

The system supports 17+ commands:

| Command | Description |
|---------|-------------|
| `@agent approve` | Approve and execute the plan |
| `@agent reject [reason]` | Reject with optional reason |
| `@agent improve <feedback>` | Request plan improvements |
| `@agent status` | Check task status |
| `@agent help` | Show all commands |
| `@agent ci-status` | Check CI/CD status |
| `@agent ci-logs` | Get failure logs |
| `@agent retry-ci` | Re-run failed CI jobs |
| `@agent ask <question>` | Ask about the codebase |
| `@agent explain <file>` | Explain what code does |
| `@agent find <pattern>` | Search in codebase |

Aliases work too: `@agent lgtm` = `@agent approve`

---

## 🎯 How It Works

### Phase 1: Discovery & Planning

When a task arrives, the **Planning Agent**:

1. **Analyzes** the error/ticket
2. **Searches** GitHub for relevant code
3. **Identifies** affected repositories and files
4. **Analyzes** Sentry stack traces (if applicable)
5. **Creates** a TDD execution plan
6. **Generates** PLAN.md with step-by-step instructions
7. **Opens** a draft PR on GitHub
8. **Sends** Slack notification for approval

**Skills Used**:
- `discovery/` - Find repo and files
- `jira-enrichment/` - Parse Jira tickets with Sentry links
- `plan-changes/` - Handle PR feedback

### Phase 2: Human Approval

The system **waits** for a human to review and approve the plan.

**What to check**:
- ✅ Correct repository identified?
- ✅ Files make sense?
- ✅ Plan approach is sound?
- ✅ Risk level acceptable?

If plan looks good → **Approve**
If plan needs changes → **Reject** with feedback

### Phase 3: Execution

Once approved, the **Executor Agent**:

1. **Clones** the repository
2. **Creates** a feature branch
3. **Writes** failing tests (RED phase)
4. **Verifies** tests fail
5. **Implements** the fix (GREEN phase)
6. **Runs** all tests to verify
7. **Commits** changes with clear messages
8. **Pushes** to the PR branch
9. **Updates** Jira ticket
10. **Sends** Slack notification

**Skills Used**:
- `git-operations/` - Git workflow
- `tdd-workflow/` - RED → GREEN → REFACTOR
- `execution/` - Orchestrate implementation
- `code-review/` - Self-review checks

---

## 🛠️ Development

### Makefile Commands

```bash
make help      # Show all commands
make setup     # Initial setup (OAuth, skills)
make skills    # Setup Claude Code skills
make up        # Start services
make down      # Stop services
make logs      # View logs
make test      # Run tests
make health    # Run health check
make tunnel    # Setup Cloudflare Tunnel (FREE webhooks!)
make clean     # Clean up Docker resources
```

### Adding a New Skill

1. Create skill directory:
   ```bash
   mkdir agents/planning-agent/skills/my-skill
   ```

2. Create `SKILL.md`:
   ```markdown
   ---
   name: my-skill
   description: What this skill does
   ---

   # My Skill

   ## Purpose
   What this skill does

   ## When to Use
   Trigger conditions

   ## MCP Tools to Use
   - `github.search_code`
   - `jira.get_issue`

   ## Process
   Step-by-step instructions

   ## Output Format
   Expected output structure
   ```

3. The worker will automatically load skills based on the SKILL.md files

---

## 🔧 MCP Configuration

The system uses Model Context Protocol (MCP) servers for tool access. Configuration is in `infrastructure/docker/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-e", "GITHUB_TOOLSETS=default,actions,code_security",
        "ghcr.io/github/github-mcp-server"
      ]
    },
    "atlassian": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://mcp.atlassian.com/v1/sse"]
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

### GitHub MCP Toolsets

The `GITHUB_TOOLSETS` environment variable enables CI monitoring:

- `default` - Core GitHub operations
- `actions` - CI/CD tools (`list_workflow_runs`, `get_job_logs`, `rerun_failed_jobs`)
- `code_security` - Security scanning tools

---

## 🌐 Production Deployment

### AWS EKS Deployment

#### 1. Setup Infrastructure

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan -var-file=environments/prod/terraform.tfvars

# Apply (creates VPC, EKS, RDS, ElastiCache, EFS)
terraform apply -var-file=environments/prod/terraform.tfvars
```

#### 2. Deploy to Kubernetes

```bash
# Configure kubectl
aws eks update-kubeconfig --name ai-agent-prod --region us-east-1

# Create namespace and resources
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/secrets.yaml
kubectl apply -f infrastructure/kubernetes/configmap.yaml

# Deploy agents and services
kubectl apply -f infrastructure/kubernetes/planning-agent/
kubectl apply -f infrastructure/kubernetes/executor-agent/
kubectl apply -f infrastructure/kubernetes/webhook-server/

# Deploy ingress
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

### Production Configuration

**Auto-scaling** (Executor Agent):
- Min replicas: 2
- Max replicas: 8
- Scale metric: Redis queue length > 2

**Resources** (per pod):
- Planning Agent: 2 vCPU, 4GB RAM
- Executor Agent: 4 vCPU, 8GB RAM

**Monthly Cost** (~$1,100):
- Claude Teams: $750 (5 seats)
- AWS Infrastructure: $350

---

## 📊 Monitoring

### Metrics Exposed

```
http://localhost:8000/metrics
```

Available metrics:
- `ai_agent_tasks_started_total` - Tasks started by agent
- `ai_agent_tasks_completed_total` - Tasks completed (success/failed)
- `ai_agent_task_duration_seconds` - Task execution time
- `ai_agent_queue_length` - Current queue size
- `ai_agent_errors_total` - Errors by type

---

## 🔐 Security

### Secrets Management

**Local Development**: `.env` file (gitignored)

**Production**: Kubernetes Secrets
```bash
kubectl create secret generic ai-agent-secrets \
  --from-literal=GITHUB_TOKEN=ghp_xxx \
  --from-literal=JIRA_API_TOKEN=xxx \
  --from-literal=SENTRY_AUTH_TOKEN=xxx \
  --from-literal=SLACK_BOT_TOKEN=xoxb-xxx \
  -n ai-agent-system
```

### Webhook Security

All webhooks validate signatures:
- **GitHub**: HMAC-SHA256
- **Jira**: Secret token + IP allowlist
- **Sentry**: Secret token

---

## 🐛 Troubleshooting

### Common Issues

#### "Claude CLI not authenticated"

```bash
# Re-authenticate
claude login

# Verify
claude --version
```

#### "MCP server not found"

```bash
# Verify Docker is running
docker ps

# Pull GitHub MCP image
docker pull ghcr.io/github/github-mcp-server

# Verify npm packages
npm list -g | grep mcp
```

#### "Queue not processing tasks"

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Check agent logs
docker-compose logs planning-agent
docker-compose logs executor-agent

# Restart agents
docker-compose restart planning-agent executor-agent
```

#### "Webhook not receiving events"

```bash
# Test locally
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -d '{"test":"data"}'

# Check webhook server logs
docker-compose logs webhook-server
```

---

## 📚 Documentation

- **[Architecture Guide](./CLAUDE-CODE-CLI.ARCHITECTURE.md)** - Detailed system design
- **[OAuth Setup Guide](./infrastructure/docker/OAUTH-SETUP.md)** - Use Claude subscription in Docker (no API key needed)
- **[Planning Agent Skills](./agents/planning-agent/skills/)** - Skill documentation
- **[Executor Agent Skills](./agents/executor-agent/skills/)** - Skill documentation

### External Resources

- [Claude Code CLI Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [MCP Protocol](https://modelcontextprotocol.io)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Sentry MCP Server](https://docs.sentry.io/product/integrations/integration-platform/mcp/)
- [Atlassian MCP](https://mcp.atlassian.com)

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)

- [x] Two-agent architecture
- [x] Official MCP integrations (GitHub, Jira, Sentry)
- [x] Local Docker Compose setup
- [x] TDD workflow enforcement
- [x] Human-in-the-loop approval
- [x] Slack notifications
- [x] Jira ticket enrichment

### ✅ Completed (v1.1 - Latest!)

- [x] **Bot Commands** - 17+ commands (`@agent approve`, `@agent ci-status`, etc.)
- [x] **Token Management** - OAuth refresh, AWS Secrets sync
- [x] **Cloudflare Tunnel** - FREE persistent webhook URLs
- [x] **Skills System** - Lazy loading (98% token savings)
- [x] **CI Monitoring** - GitHub Actions status, logs, retry
- [x] **Real TDD Workflow** - Tests before push!

### 🔮 Planned (v2.0)

- [ ] Learning from past fixes (RAG)
- [ ] Security vulnerability scanning
- [ ] Performance profiling integration
- [ ] Cost tracking per task

---

## 💰 ROI Summary

| Metric | Value |
|--------|-------|
| Monthly Cost | ~$1,100 |
| Tasks/Month (with approval) | 580 |
| Success Rate | 75% (industry benchmark) |
| Hours Saved/Month | 812 |
| Monthly Savings | $48,720 |
| **ROI** | **4,329%** |

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 💬 Support

Need help?

- **Documentation**: Check this README and architecture docs
- **Issues**: Create a GitHub issue
- **Slack**: Join #ai-agents channel

---

<p align="center">
  <strong>Built with ❤️ using Claude Code CLI</strong><br>
  <sub>Version 1.0.0 | January 2026</sub>
</p>
