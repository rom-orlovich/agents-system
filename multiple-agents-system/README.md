# AWS AgentCore Production System (Multiple Agents)

Enterprise multi-agent system using **AWS Bedrock AgentCore**, Lambda Functions, and Step Functions.

## 🚀 Quick Start

### Local Development

```bash
cd multiple-agents-system

# Install
uv venv && source .venv/bin/activate
uv pip install -e .

# Configure AWS credentials
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# Run locally
python cli.py run --ticket PROJ-123
python cli.py serve --port 8001  # Webhook server
```

### Cloud Deployment

```bash
cd infrastructure/terraform
terraform init
terraform apply -var-file=environments/prod.tfvars
```

## 🔄 GitHub PR Approval Trigger

When a planning PR is created, comment on the PR to trigger execution:

```
@agent approve
```

or

```
@agent execute
```

**What happens:**
1. Webhook receives the comment
2. Lambda creates task in DynamoDB
3. Step Functions starts execution phase
4. Execution Agent reads PLAN.md and implements
5. CI/CD Agent monitors the pipeline
6. Results posted back to PR

## 📋 Commands (Local CLI)

| Command | Description |
|---------|-------------|
| `run --ticket PROJ-123` | Run full workflow |
| `serve --port 8001` | Start webhook server |
| `agent status <id>` | Get task status |
| `monitor-sentry` | Run Sentry monitoring |
| `config` | Show configuration |

## 🤖 Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| Discovery | Claude Sonnet | Find relevant repos |
| Planning | Claude Opus | Create TDD plans |
| Execution | Claude Opus | Implement code |
| CI/CD | Claude Sonnet | Monitor pipelines |
| Sentry | Claude Sonnet | Monitor errors |
| Slack | Claude Sonnet | Handle commands |

## ⚙️ Architecture

| Local | Cloud (AWS) |
|-------|-------------|
| `LocalAgentOrchestrator` | Step Functions |
| `AgentCoreGateway` | AgentCore Gateway |
| `LocalTaskStore` | DynamoDB |
| CLI / Webhook Server | API Gateway + Lambda |

## 🌐 Webhook Endpoints

- `POST /webhooks/jira` - Jira ticket events → Start workflow
- `POST /webhooks/github` - PR comments →`@agent approve` triggers execution
- `POST /webhooks/sentry` - Error alerts → Create tickets
- `POST /webhooks/slack` - Slack commands

## 💰 Cost Analysis & ROI

> **Based on Real Claude API Pricing** - See [detailed analysis](../COST-ANALYSIS-REALISTIC.md) for full methodology
> 
> ⚠️ **Note:** Costs calculated WITHOUT prompt caching (doesn't work reliably in practice)

### Monthly Cost Breakdown (Realistic - 385 Tasks/Month)

| Component | Cost | Details |
|-----------|------|---------|
| **AWS Bedrock API** | **~$246** | Sonnet 30% / Opus 70% (no caching) |
| **AWS Infrastructure** | **~$110** | Lambda, Step Functions, DynamoDB |
| **Total** | **~$356** | Production stack |

### Capacity & Value (With Human Approval)

**The Real Bottleneck:**
- Pure agent capacity: 990 tasks/month
- With human approval (~3.5h/task): **385 tasks/month**
- System utilization: 39% (61% waiting for approval)

**Value Delivered:**
- **Capacity:** 385 tasks/month (5 parallel agents)
- **Success Rate:** 55% (custom agents)
- **Tasks Completed:** 212/month
- **Hours Saved:** 424 hours
- **Monthly Savings:** $25,440
- **Net Value:** $25,084/month
- **ROI:** 7,046%

### Comparison with Claude Code CLI

| Metric | Multiple Agents | Claude Code CLI | Winner |
|--------|-----------------|-----------------|--------|
| Monthly Cost | $356 | $1,100 | Multiple Agents (3x cheaper) |
| Capacity | 385 | 580 | **Claude Code (+50%)** |
| Success Rate | 55% | 75% | **Claude Code (+20 pts)** |
| Tasks Done | 212 | 435 | **Claude Code (2x more)** |
| Net Value | $25,084 | $51,100 | **Claude Code (2x value)** |
| Dev Effort | 2-4 weeks | 1-2 days | **Claude Code** |

> 💡 **Recommendation:** Unless you need AWS-native infrastructure, Claude Code CLI offers better value.

---

## 📚 Documentation

- [Architecture](MULTIPLE-AGENTS-SYSTEM.ARCHITECTURE.md)
- [Single-Agent System](../single-agent-system/) - Local testing version
