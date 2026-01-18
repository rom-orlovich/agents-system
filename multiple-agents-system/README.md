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

### Monthly Cost Breakdown (2,750 Tasks/Month)

| Component | Cost | Details |
|-----------|------|---------|
| **AWS Bedrock API** | **$921** | Claude Sonnet 4.5 + Opus 4.5 with 85% Prompt Caching |
| └─ Discovery Agent (15%) | $94 | Sonnet 4.5: 31.5M cached, 5.5M new, 4.5M output |
| └─ Planning Agent (25%) | $262 | Opus 4.5: 52.6M cached, 9.3M new, 7.5M output |
| └─ Execution Agent (45%) | $471 | Opus 4.5: 94.7M cached, 16.7M new, 13.6M output |
| └─ CI/CD Agent (15%) | $94 | Sonnet 4.5: 31.5M cached, 5.5M new, 4.5M output |
| **AWS Infrastructure** | **$230** | Production-grade distributed architecture |
| └─ Step Functions | $50 | 2,750 workflow executions |
| └─ Lambda (4 functions) | $40 | ~1M invocations across agents |
| └─ DynamoDB | $25 | Task state + metadata storage |
| └─ S3 + CloudWatch | $15 | Logs, artifacts, metrics |
| └─ VPC + NAT Gateway | $45 | Secure network infrastructure |
| └─ EventBridge | $10 | Webhook event routing |
| └─ Secrets Manager | $15 | Encrypted API credentials |
| └─ CloudWatch Logs | $20 | 30-day log retention |
| └─ X-Ray Tracing | $10 | Distributed request tracing |
| **Total** | **$1,151** | Full production stack |
| **Rounded Budget** | **$1,150** | Conservative estimate |

### Token Usage (Real Production Data)

**Per-Task Breakdown (90K input / 11K output avg):**

| Agent | Tasks/Mo | Input Tokens | Output Tokens | Monthly Cost |
|-------|----------|--------------|---------------|--------------|
| Discovery | 2,750 | 27.5M (85% cached) | 2.75M | $94 |
| Planning | 2,750 | 68.75M (85% cached) | 8.25M | $262 |
| Execution | 2,750 | 110M (85% cached) | 13.75M | $471 |
| CI/CD | 2,750 | 41.25M (85% cached) | 5.5M | $94 |
| **Total** | **2,750** | **247.5M** | **30.25M** | **$921** |

**Cost per Task:** $0.42 (API + Infrastructure)

### Capacity & Value

**Production Capacity:**
- **Tasks Processed:** 2,750 tasks/month (auto-scaling capacity)
- **Success Rate:** 65% (production-grade specialized agents)
- **Bugs Fixed:** 1,788 successful completions/month
- **Average Fix Time:** ~2 hours manual developer effort saved

### Department Savings (How This Saves Money)

**Direct Impact:**
- **Developer Hours Saved:** 1,788 bugs × 2 hours = **3,576 hours/month**
- **Developer Cost:** $60/hour (industry average, fully loaded)
- **Monthly Labor Savings:** **$214,560**
- **Cost per Fixed Bug:** $0.64
- **Net Monthly Gain:** $214,560 - $1,150 = **$213,410**
- **ROI:** **18,558%**
- **Break-even:** Just **20 tasks/month**

**Why This System Saves Your Department:**
1. ✅ **Eliminates 3,576 hours of manual bug fixing** - Equivalent to 21 FTEs
2. ✅ **Developers focus on high-value work** - Features, architecture, innovation
3. ✅ **Faster incident response** - < 30 min average vs 4 hours manual
4. ✅ **Reduced customer-facing downtime** - Bugs fixed before they escalate
5. ✅ **Improved team morale** - Less toil work, more creative challenges
6. ✅ **Consistent quality** - TDD methodology, automated testing, code review

### POC vs Production Comparison

| Metric | POC (Single Agent) | Production (Multiple Agents) | Improvement |
|--------|-------------------|------------------------------|-------------|
| Monthly Cost | $53 | $1,150 | 22× higher investment |
| Tasks Processed | 75 | 2,750 | **37× more volume** |
| Success Rate | 40% | 65% | **62% better accuracy** |
| Bugs Fixed | 30 | 1,788 | **60× more bugs fixed** |
| Hours Saved | 60 | 3,576 | **60× more time saved** |
| Monthly Savings | $3,600 | $214,560 | **60× higher savings** |
| ROI | 6,700% | 18,558% | 2.8× better ROI |
| Cost per Fix | $1.76 | $0.64 | **64% lower unit cost** |

**For Claude Code CLI Comparison:**
- See [root README.md](../README.md#-detailed-cost-analysis--roi) for full comparison with Claude Code CLI system ($1,550/month, 70% success rate, 2,400-4,800 tasks/month)

---

## 📚 Documentation

- [Architecture](MULTIPLE-AGENTS-SYSTEM.ARCHITECTURE.md)
- [Single-Agent System](../single-agent-system/) - Local testing version
