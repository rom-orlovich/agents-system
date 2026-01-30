# Agent Bot System

Production-ready microservices architecture for AI agent orchestration with webhook-driven task management, supporting both Claude and Cursor CLI.

## 🎯 Overview

A comprehensive system for orchestrating AI agents through webhooks from GitHub, Jira, Slack, and Sentry. Features include:

- ✅ **Multi-CLI Support**: Choose between Claude CLI or Cursor CLI (headless mode)
- ✅ **Modular Architecture**: Standalone microservices with no shared code
- ✅ **TDD Throughout**: Test-first development for all business logic
- ✅ **Strict Type Safety**: No `any` types, Pydantic validation everywhere
- ✅ **Production Ready**: Retry logic, circuit breakers, monitoring, metrics
- ✅ **Parallel Processing**: Handle multiple requests concurrently
- ✅ **Comprehensive Logging**: Centralized task flow tracking
- ✅ **Database Migrations**: SQLAlchemy + Alembic for schema management
- ✅ **Code Quality**: Pre-commit hooks, linting, auto-formatting

## 🏗️ Architecture

### Core Components

| Component           | Port | Purpose                                     |
| ------------------- | ---- | ------------------------------------------- |
| **API Gateway**     | 8080 | Webhook receiver, queue management, metrics |
| **GitHub Service**  | 8081 | GitHub API integration                      |
| **Jira Service**    | 8082 | Jira API integration                        |
| **Slack Service**   | 8083 | Slack API integration                       |
| **Sentry Service**  | 8084 | Sentry API integration                      |
| **Agent Container** | -    | Task execution with CLI runners             |
| **Dashboard API**   | 8090 | Analytics, logs, monitoring                 |

### Infrastructure

- **PostgreSQL**: Persistent storage with Alembic migrations
- **Redis**: Task queue and caching
- **Prometheus**: Metrics collection and monitoring

### Agent System

The agent container includes:

- **Agents**: Planning, Coding (see `.claude/agents/`)
- **Skills**: Analysis, Coding, Testing (see `.claude/skills/`)
- **Rules**: Type safety, No comments, TDD (see `.claude/rules/`)
- **Commands**: analyze, implement, fix (see `.claude/commands/`)
- **Hooks**: Pre-commit validation (see `.claude/hooks/`)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Make (optional)

### Installation

```bash
# 1. Setup environment
cp .env.example .env

# 2. Configure OAuth (interactive)
make oauth-setup

# 3. Build and start
make build
make up

# 4. Verify health
make test-api
```

### First Webhook Test

```bash
curl -X POST http://localhost:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -d '{
    "action": "created",
    "issue": {"number": 1, "body": "@agent analyze this"},
    "repository": {"full_name": "owner/repo"},
    "sender": {"login": "user"}
  }'
```

## 📚 Documentation

- **[docs/ARCHITECTURE_FINAL.md](./docs/ARCHITECTURE_FINAL.md)** - Complete architecture documentation
- **[docs/SETUP.md](./docs/SETUP.md)** - Complete setup guide with OAuth, database, CLI configuration
- **[docs/TESTING.md](./docs/TESTING.md)** - Testing guide and requirements

## 🧪 Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests (requires running services)
make test-integration

# E2E tests
make test-e2e

# Coverage report
make coverage
```

### Test Structure

```bash
tests/
├── test_*.py           # Unit tests (TDD)
├── integration/        # Integration tests
└── e2e/               # End-to-end tests
```

## 🛠️ Development

### Setup Development Environment

```bash
make setup-dev
```

This installs:

- pytest, pytest-asyncio, pytest-cov
- black, ruff, mypy, autoflake
- pre-commit hooks

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
mypy api-gateway/
```

### TDD Workflow

1. Write failing test
2. Implement feature
3. Run tests: `make test-unit`
4. Refactor while keeping tests green

### Architecture Principles

✅ **No `any` types** - Strict type safety enforced
✅ **No comments** - Self-explanatory code with clear naming
✅ **TDD** - Tests written before implementation
✅ **Modular** - Protocol-based interfaces, dependency injection
✅ **No shared code** - Services communicate via API/Queue only

## 📊 Monitoring & Metrics

### Prometheus Metrics

Access at: http://localhost:8080/metrics

Key metrics:

- `webhook_requests_total` - Webhook requests by provider
- `task_processing_duration_seconds` - Processing time
- `tasks_in_queue` - Current queue size
- `api_call_duration_seconds` - Microservice latency
- `cli_execution_cost_usd` - CLI execution costs
- `cli_execution_tokens` - Token usage

```bash
# View metrics summary
make metrics
```

### Dashboard Analytics

```bash
# Get analytics for last 7 days
curl "http://localhost:8090/api/v1/dashboard/analytics?period_days=7"

# View task logs
curl "http://localhost:8090/api/v1/dashboard/tasks/{task_id}/logs"
```

## 🔄 CLI Configuration

### Claude CLI (Default)

```bash
npm install -g @anthropic-ai/claude-cli
claude configure
```

### Cursor CLI (Alternative)

```bash
npm install -g @cursor/cli
cursor headless configure

# Update .env
CLI_RUNNER_TYPE=cursor
```

The system automatically uses the CLI specified in `CLI_RUNNER_TYPE`. Switch between them without code changes!

## 🔐 Error Handling

### Retry Logic

All external API calls use exponential backoff:

```python
@with_retry(config=RetryConfig(max_attempts=3, base_delay_seconds=1.0))
async def api_call():
    ...
```

### Circuit Breakers

Protect against cascading failures:

```python
@with_circuit_breaker(name="github_api", config=CircuitBreakerConfig())
async def call_github():
    ...
```

## 🔧 Database Management

```bash
# Create migration
make db-migrate message="Add new table"

# Apply migrations
make db-upgrade

# Rollback
make db-downgrade
```

## 📦 API Documentation

Interactive Swagger docs available:

- API Gateway: http://localhost:8080/docs
- GitHub Service: http://localhost:8081/docs
- Jira Service: http://localhost:8082/docs
- Slack Service: http://localhost:8083/docs
- Sentry Service: http://localhost:8084/docs
- Dashboard API: http://localhost:8090/docs

## 🤝 Contributing

1. Follow TDD - write tests first
2. Maintain type safety - no `any` types
3. Write self-explanatory code - no comments
4. Run `make format` before committing
5. Ensure all tests pass: `make test`

## 📄 License

MIT

## 🆘 Troubleshooting

See **[docs/SETUP.md](./docs/SETUP.md#troubleshooting)** for common issues and solutions.

Quick checks:

```bash
# Health check all services
./scripts/test-cli.sh health

# View logs
make logs

# Test API endpoints
make test-api
```
