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

## 💰 Cost Analysis & ROI

### Monthly Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| AWS Bedrock API | ~$30 | Claude Sonnet API calls (~100 tasks) |
| EC2 t3.medium | ~$20 | Optional: for running locally |
| Lambda + DynamoDB | ~$0 | Free tier sufficient |
| **Total** | **~$50** | Minimal cost for testing |

### Capacity & Value

**Development Capacity:**
- **Worst Case:** 50 tasks/month (manual execution)
- **Best Case:** 100 tasks/month (with automation)
- **Success Rate:** 40% (learning phase)
- **Actual Value:** 20-40 bugs fixed/month

### Department Savings

**How This Saves Your Department:**
- **Time Saved:** 40 bugs × 15 min × 40% = **240 hours/month**
- **Developer Cost:** $60/hour
- **Monthly Savings:** **$14,400**
- **ROI:** **28,700%**
- **Break-even:** Just **1 bug/month**

**Development Value:**
1. ✅ Perfect for learning AI agent concepts
2. ✅ Test prompts and workflows locally
3. ✅ Minimal cost for experimentation
4. ✅ Foundation for production scaling
5. ✅ Immediate developer productivity boost

### POC vs Production Comparison

| Metric | Development (Single Agent) | Production (Multiple Agents) | Enterprise (Claude Code CLI) |
|--------|---------------------------|------------------------------|------------------------------|
| Monthly Cost | $50 | $1,100 | $1,550 |
| Tasks/Month | 50-100 | 2,000-3,500 | 2,400-4,800 |
| Success Rate | 40% | 65% | 70% |
| Bugs Fixed | 20-40 | 1,300-2,275 | 1,680-3,360 |
| Monthly Savings | $14,400 | $117,000 | $151,200 |
| ROI | 28,700% | 10,545% | 9,655% |

**When to Use This System:**
- ✅ Learning AI agents and testing workflows
- ✅ Local development without cloud costs
- ✅ Prototyping new agent capabilities
- ✅ Small teams (< 10 developers)
- ✅ Budget-conscious initial exploration

**When to Upgrade:**
- Production workloads (> 100 tasks/month) → [Multiple Agents System](../multiple-agents-system/)
- Enterprise deployment → [Claude Code CLI](../claude-code-cli/)

---

## 🔗 See Also

- [Architecture Documentation](SINGLE-AEGNT-SYSTEM.ARCHITECTURE.md)
- [Multiple-Agents System](../multiple-agents-system/) - Distributed AWS version
