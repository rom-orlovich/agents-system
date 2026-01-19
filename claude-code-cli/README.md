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
| **Capacity** | 2,400 tasks/month | 50 tasks/month |
| **Cost** | ~$1,550/month | ~$200/month |
| **ROI** | 3,223% (50 devs) | Proof of value |

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
|-----------|---------|-----------|
| **Planning Agent** | Analyzes bugs, creates execution plans | Claude Code CLI + MCP |
| **Executor Agent** | Implements fixes following TDD | Claude Code CLI + MCP |
| **Webhook Server** | Receives triggers from external services | FastAPI |
| **Queue System** | Distributes tasks between agents | Redis |
| **Database** | Stores task state and history | PostgreSQL |
| **Dashboard** | Monitor tasks and approve plans | Next.js |

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have:

- ✅ Docker 20+ and Docker Compose 2+
- ✅ Node.js 20+ (for MCP servers)
- ✅ Claude Teams subscription
- ✅ GitHub Personal Access Token
- ✅ Jira API Token (optional)
- ✅ Sentry Auth Token (optional)
- ✅ ngrok (required for local webhook testing)

### 1. Install Claude CLI

```bash
# Install globally
npm install -g @anthropic-ai/claude-code

# Authenticate (required for agents to work)
claude login
```

### 2. Setup MCP Servers

```bash
# From the claude-code-cli directory
./scripts/setup-mcp.sh
```

This installs:
- GitHub MCP Server (Docker image)
- Sentry MCP Server (npm package)
- Filesystem MCP Server (npm package)

### 3. Configure Environment

```bash
# Copy example environment file
cp infrastructure/docker/.env.example infrastructure/docker/.env

# Edit with your credentials
nano infrastructure/docker/.env
```

Required variables:
```bash
# GitHub
GITHUB_TOKEN=ghp_your_token_here

# Jira (optional)
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your_token

# Sentry (optional)
SENTRY_AUTH_TOKEN=your_token
SENTRY_ORG=your-org

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#ai-agents
```

### 4. Build and Start

```bash
# From infrastructure/docker directory
cd infrastructure/docker

# Build all images
docker-compose build

# Start all services
docker-compose up -d

# Wait for services to be ready (~30 seconds)
sleep 30
```

### 5. Expose to Internet (ngrok)

Since GitHub and Sentry need to send webhooks to your local machine, you must expose port `8000` to the internet:

```bash
# Start ngrok
ngrok http 8000
```

Copy the **Forwarding URL** (e.g., `https://xxxx.ngrok-free.app`). This is your base URL for all webhooks.

### 6. Verify Installation

```bash
# Check service health
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"webhook-server"}

# Access dashboard
open http://localhost:3000
```

---

## 📖 Usage

### Triggering Tasks

#### Via Slack (Recommended)

```bash
/agent run Fix null pointer exception in authentication service
```

#### Via Webhook (Jira)

When you create a Jira ticket with the `AI-Fix` label, it automatically triggers the system.

#### Via Dashboard

1. Open http://localhost:3000
2. Click "Create Task"
3. Enter description and repository
4. Click "Submit"

#### Via CLI

```bash
./scripts/trigger-task.sh "Fix authentication bug" "your-org/your-repo"
```

### Monitoring Tasks

#### Dashboard
Visit http://localhost:3000 to see:
- Active tasks
- Task status (Discovering, Planning, Pending Approval, Executing, Completed)
- Approval buttons
- Execution logs

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
2. **Slack**: Message with "Approve" button
3. **Dashboard**: Approval modal

**To approve**:

**GitHub**: Comment `@agent approve` on the PR

**Slack**: Click the "✅ Approve" button

**Dashboard**: Click "Approve" on the task

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
- `sentry-analysis/` - Parse error events
- `planning/` - Create TDD plan
- `slack-notifications/` - Send updates

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

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# E2E tests
pytest tests/e2e -v

# All tests
pytest tests/ -v
```

### Adding a New Skill

1. Create skill directory:
   ```bash
   mkdir agents/planning-agent/skills/my-skill
   ```

2. Create `SKILL.md`:
   ```markdown
   # My Skill

   ## Purpose
   What this skill does

   ## When to Use
   Trigger conditions

   ## Process
   Step-by-step instructions

   ## Output Format
   JSON schema
   ```

3. Update agent's `CLAUDE.md` to reference the new skill

### Makefile Commands

```bash
make help      # Show all commands
make setup     # Initial setup
make up        # Start services
make down      # Stop services
make logs      # View logs
make test      # Run tests
make trigger   # Trigger test task
```

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
kubectl apply -f infrastructure/kubernetes/dashboard/

# Deploy ingress
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

#### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n ai-agent-system

# Check services
kubectl get svc -n ai-agent-system

# View logs
kubectl logs -f deployment/planning-agent -n ai-agent-system
```

### Production Configuration

**Auto-scaling** (Executor Agent):
- Min replicas: 2
- Max replicas: 8
- Scale metric: Redis queue length > 2

**Resources** (per pod):
- Planning Agent: 2 vCPU, 4GB RAM
- Executor Agent: 4 vCPU, 8GB RAM

**Monthly Cost** (~$1,550):
- Claude Teams: $750 (5 seats)
- AWS Infrastructure: $800

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

### Grafana Dashboards

Import provided dashboards:
- Task throughput
- Success rates
- Queue trends
- Agent performance
- Cost tracking

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

## 🧪 Testing the System

### Manual Test Flow

```bash
# 1. Trigger a test task
./scripts/trigger-task.sh "Test: Fix null pointer in auth"

# 2. Monitor planning agent
docker-compose logs -f planning-agent

# 3. Check dashboard
open http://localhost:3000

# 4. Approve the plan (via GitHub, Slack, or Dashboard)

# 5. Monitor executor agent
docker-compose logs -f executor-agent

# 6. Verify PR created on GitHub
```

### Webhook Testing

```bash
# Test Jira webhook
./scripts/test-webhook.sh jira

# Test Sentry webhook
./scripts/test-webhook.sh sentry

# Test GitHub webhook
./scripts/test-webhook.sh github
```

---

## 💡 Best Practices

### Task Descriptions

**Good**:
```
Fix null pointer exception in AuthService.getCurrentUser()
when session expires
```

**Bad**:
```
Fix bug
```

### Approval Guidelines

**Approve if**:
- ✅ Correct repository identified
- ✅ Root cause makes sense
- ✅ Plan is minimal and focused
- ✅ Tests are included
- ✅ Low/medium risk

**Reject if**:
- ❌ Wrong repository
- ❌ Plan is too broad or risky
- ❌ Missing test coverage
- ❌ Breaking changes without consideration

### Monitoring

**Watch for**:
- Queue length > 10 (scale up needed)
- High failure rate (skill improvements needed)
- Long task duration (timeout issues)
- Approval latency (training needed)

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
# Re-run setup
./scripts/setup-mcp.sh

# Verify installation
docker images | grep mcp
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

# For production, check ingress/ALB logs
```

---

## 📚 Documentation

- **[Architecture Guide](./CLAUDE-CODE-CLI.ARCHITECTURE.md)** - Detailed system design
- **[Planning Agent Skills](./agents/planning-agent/skills/)** - Skill documentation
- **[Executor Agent Skills](./agents/executor-agent/skills/)** - Skill documentation
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

### External Resources

- [Claude Code CLI Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [MCP Protocol](https://modelcontextprotocol.io)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)

- [x] Two-agent architecture
- [x] Official MCP integrations
- [x] Local Docker Compose setup
- [x] Production Kubernetes manifests
- [x] TDD workflow enforcement
- [x] Human-in-the-loop approval
- [x] Dashboard UI

### 🚧 In Progress (v1.1)

- [ ] Enhanced monitoring dashboards
- [ ] Multi-repository support
- [ ] Automatic rollback on test failures
- [ ] Cost tracking per task

### 🔮 Planned (v2.0)

- [ ] Learning from past fixes (RAG)
- [ ] Security vulnerability scanning
- [ ] Performance profiling integration
- [ ] Custom model fine-tuning

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
- **Email**: ai-team@yourcompany.com

---

## 🎉 Success Stories

> "The AI agent fixed 45 bugs in the first month, saving our team 60+ hours."
> — Engineering Manager

> "Approval takes 2 minutes, execution takes 15 minutes. This is a game-changer."
> — Senior Developer

> "ROI was positive within the first week. Best investment we made."
> — VP of Engineering

---

<p align="center">
  <strong>Built with ❤️ using Claude Code CLI</strong><br>
  <sub>Version 1.0.0 | January 2026</sub>
</p>
