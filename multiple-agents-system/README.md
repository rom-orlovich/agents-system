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

## 📚 Documentation

- [Architecture](MULTIPLE-AGENTS-SYSTEM.ARCHITECTURE.md)
- [Single-Agent System](../single-agent-system/) - Local testing version
