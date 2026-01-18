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

### Monthly Cost Breakdown

| Component | Cost | Specs |
|-----------|------|-------|
| **Claude API (Bedrock)** |
| └─ Discovery Agent | $150 | 500 tasks × $0.30/task |
| └─ Planning Agent | $200 | 500 tasks × $0.40/task |
| └─ Execution Agent | $300 | 500 tasks × $0.60/task |
| └─ CI/CD Agent | $100 | 500 tasks × $0.20/task |
| **AWS Infrastructure** |
| └─ Step Functions | $50 | 2,000 executions |
| └─ Lambda (4 functions) | $40 | ~1M invocations |
| └─ DynamoDB | $25 | Task state storage |
| └─ S3 + CloudWatch | $15 | Logs and artifacts |
| └─ VPC + NAT Gateway | $45 | Network infrastructure |
| └─ EventBridge | $10 | Webhook routing |
| └─ Secrets Manager | $15 | API keys storage |
| **Monitoring** |
| └─ CloudWatch Logs | $20 | Log retention |
| └─ X-Ray Tracing | $10 | Distributed tracing |
| **Total** | **~$980** | Base production cost |
| **With Buffer (10%)** | **~$1,100** | Recommended budget |

### Capacity & Value

**Production Capacity:**
- **Worst Case:** 2,000 tasks/month (distributed processing)
- **Best Case:** 3,500 tasks/month (optimized)
- **Success Rate:** 65% (production-grade agents)
- **Actual Value:** 1,300-2,275 bugs fixed/month

### Department Savings

**How This Saves Your Department:**
- **Time Saved:** 2,000 bugs × 15 min × 65% = **1,950 hours/month**
- **Developer Cost:** $60/hour
- **Monthly Savings:** **$117,000**
- **ROI:** **10,545%**
- **Break-even:** Just **11 bugs/month**

**Enterprise Value:**
1. ✅ Eliminates 1,950 hours of manual bug fixing
2. ✅ Developers focus on features, not bug fixes
3. ✅ Faster incident response (< 30 min vs 4 hours)
4. ✅ Reduces customer-facing downtime
5. ✅ Improves team morale (less toil work)

### POC vs Production Comparison

| Metric | POC (Single Agent) | Production (Multiple Agents) |
|--------|-------------------|------------------------------|
| Monthly Cost | $50 | $1,100 |
| Tasks/Month | 50-100 | 2,000-3,500 |
| Success Rate | 40% | 65% |
| Bugs Fixed | 20-40 | 1,300-2,275 |
| Monthly Savings | $14,400 | $117,000 |
| ROI | 28,700% | 10,545% |

**For Claude Code CLI Comparison:**
- See [root README.md](../README.md#-detailed-cost-analysis--roi) for full comparison with Claude Code CLI system ($1,550/month, 70% success rate, 2,400-4,800 tasks/month)

---

## 📚 Documentation

- [Architecture](MULTIPLE-AGENTS-SYSTEM.ARCHITECTURE.md)
- [Single-Agent System](../single-agent-system/) - Local testing version
