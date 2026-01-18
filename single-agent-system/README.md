# Single Agent System

Local implementation of the distributed multi-agent system using **AWS Bedrock** and **AgentCore MCP Gateway**.

## 🚀 Quick Start

```bash
cd single-agent-system

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e .

# Configure AWS credentials
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile  # or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY

# Run
python cli.py run --description "Add user authentication with OAuth"
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `run --ticket PROJ-123` | Run full workflow for Jira ticket |
| `run --description "..."` | Run from text description |
| `serve` | Start webhook server on port 8000 |
| `agent status <id>` | Get task status |
| `monitor-sentry` | Run Sentry monitoring |

## 🔄 GitHub PR Approval Trigger

When a planning PR is created, comment on the PR to trigger execution:

```
@agent approve
```

or

```
@agent execute
```

The agent will:
1. Read PLAN.md from the PR branch
2. Execute the implementation tasks
3. Commit changes to the PR
4. Comment with results

## 🌐 Webhook Server

```bash
# Start server
python cli.py serve --port 8000

# Expose with ngrok
ngrok http 8000
```

**Endpoints:**
- `POST /webhooks/jira` - Jira ticket events
- `POST /webhooks/github` - GitHub PR and comment events
- `POST /webhooks/sentry` - Sentry error alerts
- `POST /webhooks/slack` - Slack commands
- `GET /health` - Health check

## ⚙️ Configuration

```bash
# Required - AWS
AWS_REGION=us-east-1
AWS_PROFILE=your-profile

# Required - GitHub org
GITHUB_ORG=your-org

# Optional - MCP Gateway IDs (if using AgentCore)
GITHUB_MCP_GATEWAY_ID=...
JIRA_MCP_GATEWAY_ID=...

# Optional - Model overrides
DISCOVERY_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
PLANNING_MODEL=anthropic.claude-3-opus-20240229-v1:0
```

## 🤖 Architecture

| Component | Technology |
|-----------|------------|
| LLM | AWS Bedrock (Claude) |
| MCP Tools | AgentCore Gateway |
| Orchestration | Python AgentOrchestrator |
| Task Storage | In-memory LocalTaskStore |

## 🔗 See Also

- [Architecture Documentation](SINGLE-AEGNT-SYSTEM.ARCHITECTURE.md)
- [Multiple-Agents System](../multiple-agents-system/) - Distributed AWS version
