# Agent Bot System - Complete Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [OAuth Configuration](#oauth-configuration)
4. [Database Setup](#database-setup)
5. [CLI Configuration](#cli-configuration)
6. [Running the System](#running-the-system)
7. [Testing](#testing)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker (>= 20.10)
- Docker Compose (>= 2.0)
- Python 3.11+ (for local development)
- Make (optional, for convenience commands)

### Optional Tools
- Claude CLI or Cursor CLI (for agent execution)
- Pre-commit (for code quality hooks)

## Initial Setup

### 1. Clone and Navigate
```bash
cd agent-bot
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/agent_bot

# Redis
REDIS_URL=redis://redis:6379/0

# Logging
TASK_LOGS_DIR=/data/logs/tasks

# CLI Runner (claude or cursor)
CLI_RUNNER_TYPE=claude

# Monitoring
PROMETHEUS_ENABLED=true
```

### 3. Development Environment (Optional)
```bash
make setup-dev
```

This installs:
- pytest and testing tools
- black, ruff, mypy (code quality)
- autoflake (unused import removal)
- pre-commit hooks

## OAuth Configuration

### Automated Setup
```bash
make oauth-setup
```

Follow the interactive prompts for each service.

### Manual Setup

#### GitHub
1. Go to https://github.com/settings/developers
2. Create New OAuth App
3. Set callback URL: `http://localhost:8080/auth/github/callback`
4. Add to `.env`:
```bash
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

#### Slack
1. Go to https://api.slack.com/apps
2. Create New App → From scratch
3. OAuth & Permissions:
   - Redirect URL: `http://localhost:8080/auth/slack/callback`
   - Scopes: `chat:write`, `channels:read`, `groups:read`
4. Add to `.env`:
```bash
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

#### Jira
1. Go to https://developer.atlassian.com/console/myapps/
2. Create OAuth 2.0 integration
3. Callback URL: `http://localhost:8080/auth/jira/callback`
4. Permissions: `read:jira-work`, `write:jira-work`
5. Add to `.env`:
```bash
JIRA_CLIENT_ID=your_client_id
JIRA_CLIENT_SECRET=your_client_secret
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_api_token
```

#### Sentry
1. Go to https://sentry.io/settings/account/api/auth-tokens/
2. Create New Token
3. Scopes: `project:read`, `project:write`
4. Add to `.env`:
```bash
SENTRY_AUTH_TOKEN=your_auth_token
SENTRY_ORGANIZATION=your_org_slug
```

## Database Setup

### Initialize Database
```bash
# Start database
docker-compose up -d postgres

# Run migrations
make db-upgrade
```

### Create New Migration
```bash
make db-migrate message="Add new table"
```

### Migration Management
```bash
# Upgrade to latest
make db-upgrade

# Downgrade one version
make db-downgrade
```

## CLI Configuration

### Claude CLI (Default)
```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-cli

# Configure
claude configure

# Test
claude run "Hello, world!"
```

### Cursor CLI (Alternative)
```bash
# Install Cursor CLI
npm install -g @cursor/cli

# Configure for headless mode
cursor headless configure

# Update .env
CLI_RUNNER_TYPE=cursor

# Test
cursor headless run --directory /tmp "Hello!"
```

### Switching CLIs
The system automatically uses the CLI specified in `CLI_RUNNER_TYPE`. Both can be installed simultaneously.

## Running the System

### Full System
```bash
# Build all services
make build

# Start all services
make up

# View logs
make logs

# Stop all services
make down
```

### Individual Services
```bash
# Start specific service
docker-compose up -d api-gateway

# View service logs
docker-compose logs -f api-gateway

# Restart service
docker-compose restart api-gateway
```

### Health Checks
```bash
# Test all health endpoints
./scripts/test-cli.sh health

# Or use make
make test-api
```

## Testing

### Unit Tests
```bash
make test-unit
```

### Integration Tests
```bash
# Start services first
make up

# Run integration tests
make test-integration
```

### E2E Tests
```bash
make test-e2e
```

### Test Coverage
```bash
make coverage
```

View report at `htmlcov/index.html`

### Manual API Testing
```bash
# Test GitHub webhook
./scripts/test-cli.sh github

# Test Jira webhook
./scripts/test-cli.sh jira

# Test metrics
./scripts/test-cli.sh metrics

# Test dashboard
./scripts/test-cli.sh dashboard
```

## Monitoring

### Prometheus Metrics
Access metrics at: http://localhost:8080/metrics

Key metrics:
- `webhook_requests_total` - Total webhook requests by provider and status
- `task_processing_duration_seconds` - Task processing time histogram
- `tasks_in_queue` - Current queue size
- `api_call_duration_seconds` - Microservice call durations
- `cli_execution_cost_usd` - Total CLI execution costs
- `cli_execution_tokens` - Token usage (input/output)

```bash
# View metrics summary
make metrics
```

### Dashboard API
Access analytics at: http://localhost:8090/api/v1/dashboard/analytics

```bash
# Get analytics for last 7 days
curl "http://localhost:8090/api/v1/dashboard/analytics?period_days=7"

# View task logs
curl "http://localhost:8090/api/v1/dashboard/tasks/{task_id}/logs"
```

### Service Health
All services provide `/health` endpoints:
- API Gateway: http://localhost:8080/health
- GitHub Service: http://localhost:8081/health
- Jira Service: http://localhost:8082/health
- Slack Service: http://localhost:8083/health
- Sentry Service: http://localhost:8084/health
- Dashboard API: http://localhost:8090/health

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
lsof -i :8080

# Change port in docker-compose.yml
ports:
  - "8081:8080"  # Use 8081 externally
```

#### Database Connection Failed
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

#### Redis Connection Failed
```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### OAuth Errors
```bash
# Verify environment variables
docker-compose exec api-gateway env | grep GITHUB

# Check webhook signature
# Ensure GITHUB_WEBHOOK_SECRET matches GitHub settings
```

#### Task Not Processing
```bash
# Check queue
docker-compose exec redis redis-cli
> ZCARD tasks

# Check worker logs
docker-compose logs agent-container

# Verify CLI is configured
docker-compose exec agent-container claude --version
# or
docker-compose exec agent-container cursor --version
```

### Log Locations

Container logs:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs api-gateway -f
```

Task logs:
```bash
# Inside container
ls -la /data/logs/tasks/{task_id}/

# From host (if mounted)
ls -la ./data/logs/tasks/{task_id}/
```

### Debugging

#### Enable Debug Logging
Add to `.env`:
```bash
LOG_LEVEL=DEBUG
```

#### Access Container Shell
```bash
docker-compose exec api-gateway /bin/bash
```

#### Test Database Connection
```bash
docker-compose exec api-gateway python -c "
from storage.database import engine
import asyncio
asyncio.run(engine.connect())
print('Connected!')
"
```

#### Test Redis Connection
```bash
docker-compose exec api-gateway python -c "
import redis.asyncio as redis
import asyncio
async def test():
    client = await redis.from_url('redis://redis:6379/0')
    await client.ping()
    print('Connected!')
asyncio.run(test())
"
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature
```

### 2. Write Tests First (TDD)
```bash
# Create test file
touch api-gateway/tests/test_new_feature.py

# Write failing test
# Implement feature
# Run tests
make test-unit
```

### 3. Code Quality
```bash
# Format code
make format

# Run linting
make lint

# Check types
mypy api-gateway/
```

### 4. Pre-commit Hooks
Hooks run automatically on commit:
- Trailing whitespace removal
- JSON/YAML validation
- Black formatting
- Ruff linting
- Autoflake (unused imports)
- MyPy type checking

Skip hooks (not recommended):
```bash
git commit --no-verify
```

### 5. Test Before Commit
```bash
# Unit tests
make test-unit

# Integration tests (if services running)
make test-integration

# All tests
make test
```

## Production Deployment

### Build Production Images
```bash
docker-compose -f docker-compose.prod.yml build
```

### Environment Variables
Ensure all production values are set:
- Strong database passwords
- Production URLs
- Valid OAuth credentials
- Webhook secrets

### Database Backups
```bash
# Backup
docker-compose exec postgres pg_dump -U postgres agent_bot > backup.sql

# Restore
cat backup.sql | docker-compose exec -T postgres psql -U postgres agent_bot
```

### Scaling Workers
```bash
# Scale agent workers
docker-compose up -d --scale agent-container=5
```

### Health Monitoring
Set up external monitoring for all `/health` endpoints.

## Additional Resources

- **API Documentation**: http://localhost:8080/docs
- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Project Summary**: See [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
- **Agent Configuration**: See [agent-container/.claude/claude.md](./agent-container/.claude/claude.md)

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `make logs`
3. Test services: `make test-api`
4. Create GitHub issue with logs and error details
