# 🤖 AI Agent Production System

> **Enterprise-grade autonomous AI agents for code management powered by Claude**

A comprehensive suite of AI-powered agents that automate the software development lifecycle—from error detection to code fixes, testing, and pull request creation.

---

## ✨ Overview

This monorepo contains three interconnected systems that demonstrate different approaches to building autonomous AI agents:

| System | Description | Use Case |
|--------|-------------|----------|
| **[Single Agent System](./single-agent-system/)** | Local orchestration with AWS Bedrock | Development & Testing |
| **[Multiple Agents System](./multiple-agents-system/)** | Distributed AWS architecture | Production Deployment |
| **[Claude Code CLI POC](./claude-code-cli-poc/)** | Docker-based two-agent system | Quick Proof of Concept |

---

## 🚀 Key Features

- **🔄 End-to-End Automation** — From Sentry alerts to merged PRs, fully automated
- **🧠 Multi-Agent Architecture** — Specialized agents for discovery, planning, execution, CI/CD, and monitoring
- **🔗 MCP Integration** — Official Model Context Protocol servers for GitHub, Jira, and Sentry
- **☁️ AWS Native** — Built on Bedrock, Lambda, Step Functions, and AgentCore
- **💬 Slack Integration** — Human-in-the-loop approval workflows
- **🐳 Docker Ready** — Easy local development and deployment

---

## 📋 The Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Sentry    │────▶│    Jira      │────▶│  AI Agents   │────▶│  GitHub PR   │
│    Alert     │     │   Ticket     │     │  (Plan+Fix)  │     │  + Tests     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │ @agent       │
                                         │ approve      │
                                         └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  Execution   │
                                         │  + CI/CD     │
                                         └──────────────┘
```

---

## 🏗️ Architecture Comparison

| Feature | Single Agent | Multiple Agents | CLI POC |
|---------|--------------|-----------------|---------|
| **LLM Provider** | AWS Bedrock | AWS Bedrock | Claude CLI |
| **Orchestration** | Python | Step Functions | Docker Compose |
| **Tool Access** | AgentCore MCP | AgentCore MCP | MCP Servers |
| **State Storage** | In-memory | DynamoDB | File-based |
| **Best For** | Local dev | Production | Quick demos |

---

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- GitHub Personal Access Token
- Jira API Token
- Claude Teams subscription (for CLI POC)

### Single Agent System (Recommended for Development)

```bash
cd single-agent-system

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run
python cli.py run --description "Fix authentication bug in login flow"
```

### Multiple Agents System (Production)

```bash
cd multiple-agents-system

# Local testing
uv venv && source .venv/bin/activate
uv pip install -e .
python cli.py run --ticket PROJ-123

# Deploy to AWS
cd infrastructure/terraform
terraform init
terraform apply
```

### Claude Code CLI POC (Docker)

```bash
cd claude-code-cli-poc

# Configure
cp .env.example .env

# Build and run
docker-compose up -d

# Test webhook
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{"issue":{"key":"TEST-123","fields":{"summary":"Fix bug","labels":["AI-Fix"]}}}'
```

---

## 🤖 Agent Roles

| Agent | Responsibility | Model |
|-------|----------------|-------|
| **Discovery** | Analyze tickets, find relevant repositories | Claude Sonnet |
| **Planning** | Create TDD implementation plans | Claude Opus |
| **Execution** | Write code, run tests, create PRs | Claude Opus |
| **CI/CD** | Monitor and fix pipeline failures | Claude Sonnet |
| **Sentry** | Process error alerts, create tickets | Claude Sonnet |
| **Slack** | Handle commands and approvals | Claude Sonnet |

---

## 🔗 Webhook Endpoints

All systems expose similar webhook endpoints:

| Endpoint | Trigger | Action |
|----------|---------|--------|
| `POST /webhooks/jira` | Ticket created with `AI-Fix` label | Start discovery & planning |
| `POST /webhooks/github` | PR comment with `@agent approve` | Execute implementation |
| `POST /webhooks/sentry` | New error alert | Create Jira ticket |
| `POST /webhooks/slack` | `/agent` command | Various agent actions |
| `GET /health` | - | Health check |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [docs/poc-implementation-guide.md](./docs/poc-implementation-guide.md) | Step-by-step POC setup guide |
| [docs/ai-agent-production-system-v4.md](./docs/ai-agent-production-system-v4.md) | Production architecture design |
| [docs/AWS-AGENTCORE-PRODUCTION-IMPLEMENTATION.md](./docs/AWS-AGENTCORE-PRODUCTION-IMPLEMENTATION.md) | AWS AgentCore implementation details |

### System-Specific Architecture

- [Single Agent Architecture](./single-agent-system/SINGLE-AEGNT-SYSTEM.ARCHITECTURE.md)
- [Multiple Agents Architecture](./multiple-agents-system/MULTIPLE-AGENTS-SYSTEM.ARCHITECTURE.md)
- [CLI POC Architecture](./claude-code-cli-poc/CLAUDE-CODE-CLI-POC.ARCHITECTURE.md)

---

## ⚙️ Configuration

### Required Environment Variables

```bash
# AWS (for Bedrock/AgentCore)
AWS_REGION=us-east-1
AWS_PROFILE=your-profile

# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_ORG=your-org

# Jira
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-token
JIRA_PROJECT=PROJ

# Sentry
SENTRY_AUTH_TOKEN=your-token
SENTRY_ORG=your-org

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL=#ai-agent
```

---

## 🔒 Security Considerations

- Store all secrets in AWS Secrets Manager for production
- Use IAM roles with least-privilege access
- Validate webhook signatures (Jira, GitHub, Sentry)
- Run agents in isolated Docker containers
- Enable audit logging in CloudWatch

---

## 💰 Cost Estimation

| Component | Monthly Cost (Est.) |
|-----------|---------------------|
| Claude Teams | $150/seat |
| EC2 t3.large | ~$45 |
| AWS Extras (Lambda, Step Functions, DynamoDB) | ~$10-20 |
| **Total POC** | **~$200** |

---

## 📊 Project Structure

```
agents-prod/
├── single-agent-system/       # Local orchestration system
│   ├── agents/                # Agent implementations
│   ├── services/              # LLM, gateway, storage services
│   ├── prompts/               # Agent system prompts
│   └── config/                # Configuration management
│
├── multiple-agents-system/    # Distributed AWS system
│   ├── agents/                # Agent implementations
│   ├── lambda/                # AWS Lambda handlers
│   ├── infrastructure/        # Terraform IaC
│   └── prompts/               # Agent system prompts
│
├── claude-code-cli-poc/       # Docker-based POC
│   ├── webhook-server/        # FastAPI webhook receiver
│   ├── planning-agent/        # Planning & discovery
│   ├── executor-agent/        # Code execution
│   └── shared/                # Shared utilities
│
└── docs/                      # Documentation
    ├── poc-implementation-guide.md
    ├── ai-agent-production-system-v4.md
    └── AWS-AGENTCORE-PRODUCTION-IMPLEMENTATION.md
```

---

## 🗺️ Roadmap

- [x] Core agent framework
- [x] MCP integration (GitHub, Jira, Sentry)
- [x] AWS Bedrock integration
- [x] Webhook server for all triggers
- [x] PR approval workflow (`@agent approve`)
- [ ] Multi-repo support
- [ ] Enhanced code review agent
- [ ] Cost optimization recommendations
- [ ] Fine-tuned models for specific domains

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is proprietary software. All rights reserved.

---

<p align="center">
  <b>Built with ❤️ using Claude</b>
</p>
