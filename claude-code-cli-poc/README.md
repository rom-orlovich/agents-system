# Claude Code CLI POC - Two Agent System

A proof-of-concept for running Claude Code CLI with two separate agents:

1. **Planning & Discovery Agent** - Analyzes Jira tickets, discovers relevant repos, creates implementation plans
2. **Executor Agent** - Implements code changes following the approved plan, runs tests, creates PRs

## Architecture

```
Jira/Sentry → Webhook Server → Planning Agent → Draft PR
                    ↓
GitHub PR Comment "@agent approve" → Webhook Server → Executor Agent
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Claude CLI authenticated (`claude login` on host machine)
- GitHub Personal Access Token
- Jira API Token

### Setup

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Build and start:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Configure webhooks:**
   - Jira: Add webhook to `http://your-server:8000/jira-webhook`
   - Sentry: Add webhook to `http://your-server:8000/sentry-webhook`
   - GitHub: Add webhook to `http://your-server:8000/github-webhook`

### Testing Locally

```bash
# Test Jira webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{"issue":{"key":"TEST-123","fields":{"summary":"Test bug","labels":["AI-Fix"]}}}'

# Test GitHub PR approval
curl -X POST http://localhost:8000/github-webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"created","comment":{"body":"@agent approve"},"pull_request":{"number":1}}'
```

## Directory Structure

```
claude-code-cli-poc/
├── docker-compose.yml          # Service orchestration
├── pyproject.toml              # Python project config (uv)
├── .env.example                # Environment template
├── webhook-server/             # FastAPI webhook receiver
├── planning-agent/             # Planning & Discovery agent
├── executor-agent/             # Code execution agent
├── shared/                     # Shared utilities
└── scripts/                    # Deployment scripts
```

## PR Approval Triggers

The executor agent is triggered when a reviewer comments on a planning PR with:
- `@agent approve`
- `/approve`
- `LGTM`

## Deployment to EC2

```bash
./scripts/deploy.sh
```

See [scripts/setup-machine.sh](scripts/setup-machine.sh) for machine setup.
