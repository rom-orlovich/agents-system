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

> **Based on Real Claude API Pricing** - See [detailed analysis](../COST-ANALYSIS-REALISTIC.md) for methodology
> 
> ⚠️ **Note:** Costs calculated WITHOUT prompt caching (doesn't work reliably in practice)

### Monthly Cost Breakdown (Realistic - 77 Tasks/Month)

| Component | Cost | Details |
|-----------|------|---------|
| **AWS Bedrock API** | **~$15** | Sonnet + Opus mix (no caching) |
| **AWS Infrastructure** | **~$25** | EC2 t3.small + basic AWS |
| **Total** | **~$40** | Development environment |

### Capacity & Value (With Human Approval)

**The Real Bottleneck:**
- Pure agent capacity: 264 tasks/month
- With human approval (~3.5h/task): **77 tasks/month**
- System utilization: 29% (71% waiting for approval)

**Value Delivered:**
- **Capacity:** 77 tasks/month (single agent)
- **Success Rate:** 50% (custom agent)
- **Tasks Completed:** 39/month
- **Hours Saved:** 78 hours
- **Monthly Savings:** $4,680
- **Net Value:** $4,640/month
- **ROI:** 11,600%

### Comparison with Other Systems

| Metric | Single Agent | Multiple Agents | Claude Code CLI |
|--------|--------------|-----------------|-----------------|
| Monthly Cost | $40 | $356 | $1,100 |
| Capacity | 77 | 385 | 580 |
| Success Rate | 50% | 55% | **75%** |
| Tasks Done | 39 | 212 | **435** |
| Net Value | $4,640 | $25,084 | **$51,100** |
| Dev Effort | 2-4 weeks | 2-4 weeks | **1-2 days** |

> 💡 **Recommendation:** Use for learning/testing only. For production, prefer Claude Code CLI.

**When to Use This System:**
- ✅ Learning AI agents and testing workflows
- ✅ Local development without cloud costs
- ✅ Small teams (< 10 developers)

**When to Upgrade:**
- Production workloads (> 50 tasks/month) → [Claude Code CLI](../claude-code-cli/)
- AWS-native required → [Multiple Agents System](../multiple-agents-system/)

---

## 🔗 See Also

- [Architecture Documentation](SINGLE-AEGNT-SYSTEM.ARCHITECTURE.md)
- [Multiple-Agents System](../multiple-agents-system/) - Distributed AWS version
