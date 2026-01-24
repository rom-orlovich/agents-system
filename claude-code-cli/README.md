# 🤖 Claude Code CLI - AI Agent System

> **Autonomous bug fixing powered by Claude Code CLI and MCP**

A two-agent system (Planning + Executor) that autonomously analyzes bugs, creates fix plans, and implements solutions with TDD workflow - all using Claude Code CLI with Model Context Protocol (MCP) integrations.

---

## 🎯 What It Does

Automates the complete bug-fixing workflow:

```
Sentry/Jira → Planning Agent → Human Approval → Executor Agent → PR Ready
  (Error)     (Analyze+Plan)   (@agent approve)   (Fix+Test)      (Review)
```

**Key Features:**
- 🔍 Analyzes errors from Sentry/Jira
- 📂 Discovers affected repositories and files  
- 📝 Creates TDD-based fix plans
- ⏸️ Waits for human approval
- ✅ Implements fixes with tests
- 🔄 Creates pull requests
- 📢 Updates Jira and Slack  

---

## 🏗️ Architecture

```
Webhooks → Webhook Server → Redis Queue → Agents → MCP Tools
(Trigger)    (FastAPI)      (planning/     (Claude   (GitHub/
                            execution)      Code)    Jira/etc)
                                              ↓
                                          Dashboard
                                          (Status/Metrics)
```

### Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Planning Agent** | Analyzes bugs, creates fix plans | Claude Code CLI + MCP |
| **Executor Agent** | Implements fixes with TDD | Claude Code CLI + MCP |
| **Webhook Server** | Receives webhooks from Sentry/Jira/GitHub | FastAPI |
| **Dashboard**      | Real-time status, metrics, and session data | Go + HTML/JS |
| **Redis Queue** | Task distribution between agents | Redis |
| **MCP Servers** | Tool access (GitHub, Jira, Sentry) | Official MCP servers |

---

## 📂 Project Structure

```
claude-code-cli/
├── agents/
│   ├── planning-agent/          # Analyzes bugs, creates plans
│   │   ├── worker.py            # Queue consumer
│   │   └── skills/              # Planning skills (discovery, jira-enrichment, etc)
│   └── executor-agent/          # Implements fixes
│       ├── worker.py            # TDD executor
│       └── skills/              # Execution skills (git-ops, tdd-workflow, etc)
│
│   └── dashboard/               # Real-time dashboard
│       ├── main.go              # Go server
│       └── static/              # Frontend assets
│
├── services/
│   └── webhook-server/          # FastAPI webhook receiver
│       ├── main.py
│       └── routes/              # GitHub, Jira, Slack, Sentry webhooks
│
├── shared/                      # Shared utilities
│   ├── models.py                # Pydantic task models
│   ├── task_queue.py            # Redis queue operations
│   ├── commands/                # Bot command system (@agent approve, etc)
│   └── ...                      # Config, logging, metrics, etc
│
├── infrastructure/docker/
│   ├── docker-compose.yml       # Local development
│   ├── mcp.json                 # MCP server configuration
│   └── extract-oauth.sh         # OAuth credential extraction
│
└── scripts/                     # Setup and maintenance scripts
```

---

## 🚀 Quick Start

### Prerequisites

- Docker 20+ and Docker Compose 2+
- Node.js 20+ (for MCP servers)
- Python 3.12+ (managed via `uv`)
- `uv` package manager (optional, for local dev)
- Claude Pro/Teams subscription **OR** `ANTHROPIC_API_KEY`
- GitHub Personal Access Token
- (Optional) Jira API Token, Sentry Auth Token, Slack Bot Token

### Setup

**1. Install Claude CLI**
```bash
npm install -g @anthropic-ai/claude-code
claude login  # Authenticate
```

**2. Configure Environment**
```bash
cp infrastructure/docker/.env.example infrastructure/docker/.env
# Edit .env with your tokens
```

Required variables:
```bash
GITHUB_TOKEN=ghp_your_token_here

# Optional (if not using OAuth)
ANTHROPIC_API_KEY=sk-ant-xxx

# Optional integrations
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your_token
SENTRY_AUTH_TOKEN=your_token
SLACK_BOT_TOKEN=xoxb-your-token
```

**3. Start the System**
```bash
make start  # Builds images, extracts OAuth, starts services
```

**4. Expose Webhooks (ngrok)**
```bash
# Get free static domain at ngrok.com
make tunnel NGROK_DOMAIN=your-name.ngrok-free.app
```

**5. Verify**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

> **OAuth vs API Key**: If you have Claude Pro/Teams, use OAuth (free with subscription). Otherwise, set `ANTHROPIC_API_KEY`. See [OAUTH-SETUP.md](./infrastructure/docker/OAUTH-SETUP.md) for details.

---

## � Usage

### Triggering Tasks

**Via Jira Webhook** (Automatic)
When Sentry creates a Jira ticket, the system automatically analyzes and creates a fix plan.

**Via GitHub Comment**
Comment `@agent approve` on any PR to trigger execution.

**Via Slack** (If configured)
```
/agent run Fix null pointer exception in auth service
```

### Bot Commands

Supported commands (use in GitHub PR comments or Slack):

| Command | Description |
|---------|-------------|
| `@agent approve` | Approve and execute the plan |
| `@agent reject [reason]` | Reject with optional reason |
| `@agent improve <feedback>` | Request plan improvements |
| `@agent status` | Check task status |
| `@agent ci-status` | Check CI/CD status |
| `@agent ci-logs` | Get failure logs |
| `@agent retry-ci` | Re-run failed CI jobs |
| `@agent help` | Show all commands |

Aliases: `@agent lgtm` = `@agent approve`

### Monitoring

**View Logs**
```bash
docker-compose logs -f              # All services
docker-compose logs -f planning-agent
docker-compose logs -f executor-agent
```

**Check Metrics**
```bash
curl http://localhost:8000/metrics  # Prometheus metrics
```

**View Dashboard**
Open `http://localhost:8080` to see real-time task status, session metrics, and costs.
```

---

## ⚙️ How It Works

### Phase 1: Planning

The **Planning Agent**:
1. Analyzes the error/ticket
2. Searches GitHub for relevant code
3. Analyzes Sentry stack traces (if applicable)
4. Creates a TDD execution plan (PLAN.md)
5. Opens a draft PR and notifies via Slack

**Skills**: `discovery`, `jira-enrichment`, `plan-changes`

### Phase 2: Approval

Human reviews the plan and either:
- ✅ **Approves** → Task moves to execution queue
- ❌ **Rejects** → Provides feedback for plan revision

### Phase 3: Execution

The **Executor Agent**:
1. Clones repository and creates branch
2. Writes failing tests (RED)
3. Implements the fix (GREEN)
4. Runs all tests to verify
5. Commits and pushes to PR
6. Updates Jira and Slack

**Skills**: `git-operations`, `tdd-workflow`, `execution`, `code-review`

---

## 🛠️ Development

### Makefile Commands

```bash
# 🚀 Main Commands
make start     # 🎯 ONE COMMAND: setup + build + start
make up        # Start services (quick)
make down      # Stop services
make restart   # Restart services
make rebuild   # Rebuild images (use if you changed deps)
make logs      # View logs

# 🔧 Utilities
make oauth     # Refresh OAuth credentials
make env       # Edit .env file
make health    # Health check
make tunnel    # Start webhook tunnel
make clean     # Cleanup everything
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

## 📊 Monitoring

**Prometheus Metrics** (`http://localhost:8000/metrics`):
- `ai_agent_tasks_started_total` - Tasks started
- `ai_agent_tasks_completed_total` - Tasks completed (success/failed)
- `ai_agent_task_duration_seconds` - Execution time
- `ai_agent_queue_length` - Queue size
- `ai_agent_errors_total` - Errors by type

---

## 🔐 Security

**Secrets**: Stored in `.env` file (gitignored)

**Webhook Validation**:
- GitHub: HMAC-SHA256 signature
- Jira: Secret token + IP allowlist
- Sentry: Secret token

---

## 🐛 Troubleshooting

**Claude CLI not authenticated**
```bash
claude login && claude --version
```

**MCP server not found**
```bash
docker pull ghcr.io/github/github-mcp-server
npm list -g | grep mcp
```

**Queue not processing**
```bash
docker-compose logs planning-agent
docker-compose restart planning-agent executor-agent
```

**Webhook not receiving events**
```bash
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" -d '{"test":"data"}'
docker-compose logs webhook-server
```

---

## 📚 Resources

- [Architecture Guide](./CLAUDE-CODE-CLI.ARCHITECTURE.md) - Detailed system design
- [OAuth Setup](./infrastructure/docker/OAUTH-SETUP.md) - Use Claude subscription in Docker
- [Claude Code CLI Docs](https://docs.anthropic.com/claude/docs/claude-code)
- [MCP Protocol](https://modelcontextprotocol.io)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)

---

## 🗺️ Roadmap

**Completed**:
- ✅ Two-agent architecture with MCP
- ✅ Bot commands (`@agent approve`, etc.)
- ✅ OAuth token management
- ✅ Skills system with lazy loading
- ✅ TDD workflow enforcement
- ✅ CI/CD monitoring

**Planned**:
- 🔮 Learning from past fixes (RAG)
- 🔮 Security vulnerability scanning
- 🔮 Performance profiling
- 🔮 Cost tracking per task



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
