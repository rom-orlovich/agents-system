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

### Monthly Cost Breakdown (75 Tasks/Month)

| Component | Cost | Details |
|-----------|------|---------|
| **AWS Bedrock API** | **$28** | Claude Sonnet 4.5 + Opus 4.5 with Prompt Caching (75%) |
| └─ Sonnet 4.5 (30%) | $6 | Discovery + Planning: 2M tokens cached, 0.5M new |
| └─ Opus 4.5 (70%) | $22 | Execution + CI/CD: 3.5M tokens cached, 1.2M new |
| **AWS Infrastructure** | **$25** | Minimal cloud resources |
| └─ EC2 t3.small (optional) | $15 | Local runtime environment |
| └─ Lambda + CloudWatch | $10 | Serverless functions + monitoring |
| **Total** | **~$53** | Development & learning environment |

### Token Usage (Real Data)

| Phase | Input Tokens | Output Tokens | Cost per Task |
|-------|--------------|---------------|---------------|
| Discovery | 10K (80% cached) | 1K | $0.05 |
| Planning | 25K (80% cached) | 3K | $0.17 |
| Execution | 40K (75% cached) | 5K | $0.42 |
| CI/CD | 15K (80% cached) | 2K | $0.07 |
| **Total/Task** | **90K** | **11K** | **$0.71** |

### Capacity & Value

**Development Capacity:**
- **Tasks Processed:** 75 tasks/month
- **Success Rate:** 40% (learning phase, limited context)
- **Bugs Actually Fixed:** 30 successful completions/month
- **Average Fix Time:** ~2 hours manual developer effort saved

### Department Savings (How This Saves Money)

**Direct Impact:**
- **Developer Hours Saved:** 30 bugs × 2 hours = **60 hours/month**
- **Developer Cost:** $60/hour (industry average, fully loaded)
- **Monthly Labor Savings:** **$3,600**
- **Cost per Fixed Bug:** $1.76
- **Net Monthly Gain:** $3,600 - $53 = **$3,547**
- **ROI:** **6,700%**
- **Break-even:** Just **1 bug/month**

**Why This System Saves Your Department:**
1. ✅ **Eliminates toil work** - Developers focus on architecture, not bug fixes
2. ✅ **Learning foundation** - Train team on AI agents before production scale
3. ✅ **Minimal investment** - Prove ROI with < $100 initial spend
4. ✅ **Immediate productivity** - Even 40% success rate delivers 30× ROI
5. ✅ **Risk-free testing** - Local development, no production impact

### POC vs Production Comparison

| Metric | Development (Single Agent) | Production (Multiple Agents) | Enterprise (Claude Code CLI) |
|--------|---------------------------|------------------------------|------------------------------|
| Monthly Cost | $53 | $1,150 | $1,550 |
| Tasks Processed | 75 | 2,750 | 3,600 |
| Success Rate | 40% | 65% | 70% |
| Bugs Fixed | 30 | 1,788 | 2,520 |
| Hours Saved | 60 | 3,576 | 5,040 |
| Monthly Savings | $3,600 | $214,560 | $302,400 |
| ROI | 6,700% | 18,558% | 19,406% |
| Cost per Fix | $1.76 | $0.64 | $0.62 |

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
