# Agent Bot - Production Containerized Agent System

Production-ready microservices-based AI agent system with 14+ Docker containers for autonomous code management, bug fixing, and development automation.

## Architecture Overview

**14 Containers:**
- 3x Agent Engine (scalable workers, ports 8080-8089)
- 4x MCP Servers (GitHub:9001, Jira:9002, Slack:9003, Sentry:9004)
- 4x API Services (GitHub:3001, Jira:3002, Slack:3003, Sentry:3004)
- API Gateway (port 8000)
- Dashboard API (port 8090)
- External Dashboard (port 3005)
- Knowledge Graph (port 4000)
- Redis (port 6379)
- PostgreSQL (port 5432)

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)

**Completed:**
- ✅ Shared packages (config, logging, metrics, models)
- ✅ API clients (GitHub, Jira, Slack, Sentry) - all <300 lines
- ✅ Docker infrastructure (Redis, PostgreSQL)
- ✅ API Gateway with health check
- ✅ Makefile targets (init, build, up, down, health)
- ✅ Unit tests for shared packages and clients
- ✅ Project structure and documentation

**Verification:**
```bash
# Initialize environment
make init

# Build Phase 1 containers
make build

# Start infrastructure
make up

# Check health
make health
# Expected: {"status": "healthy", "service": "api-gateway"}

# Run unit tests
make test-unit
# Expected: All tests pass in <5 seconds
```

### 🚧 Phase 2: API Services Layer (IN PROGRESS)

- [ ] 4 API services with auth, rate limiting, health checks
- [ ] Middleware (auth, rate limiter, error handler)
- [ ] Integration tests for API services
- [ ] docker-compose.services.yml

### 📋 Phase 3: MCP Servers (PLANNED)

- [ ] Official GitHub MCP server
- [ ] Atlassian Jira MCP server
- [ ] Custom Slack MCP server (FastMCP)
- [ ] Custom Sentry MCP server (FastMCP)
- [ ] docker-compose.mcp.yml

### 📋 Phase 4: Agent Engine Core (PLANNED)

- [ ] Multi-CLI support (Claude Code CLI + Cursor CLI)
- [ ] Async Redis queue consumer
- [ ] Dynamic skill loading
- [ ] MCP server integration
- [ ] docker-compose.agent.yml with scaling

### 📋 Phase 5: Dashboards (PLANNED)

- [ ] Internal dashboard API (port 8090)
- [ ] External React dashboard (port 3005)
- [ ] Real-time log streaming (SSE)
- [ ] Analytics and metrics

### 📋 Phase 6: Webhooks & Knowledge Graph (PLANNED)

- [ ] Webhook handlers (GitHub, Jira, Slack, Sentry)
- [ ] Signature validation
- [ ] Knowledge Graph (Rust-based)
- [ ] Entity extraction and relationship management

### 📋 Phase 7: Production Readiness (PLANNED)

- [ ] Security audit (Trivy, Snyk)
- [ ] Monitoring (Prometheus, Grafana)
- [ ] Load testing (100+ concurrent tasks)
- [ ] CI/CD pipeline
- [ ] Backup/recovery procedures

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Make
- Git

### Installation

```bash
# Clone repository
git clone <repo-url>
cd agent-bot

# Initialize environment
make init

# Edit .env with your API keys
nano .env

# Build containers
make build

# Start services
make up

# Check health
make health
```

### Environment Configuration

Required environment variables in `.env`:

```bash
# Infrastructure
REDIS_URL=redis://redis:6379/0
POSTGRES_URL=postgresql://agent:password@postgres:5432/agents_system

# CLI Provider
CLI_PROVIDER=claude-code-cli  # or cursor-cli

# External APIs
GITHUB_TOKEN=ghp_xxxxx
JIRA_API_KEY=xxxxx
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=you@example.com
SLACK_BOT_TOKEN=xoxb-xxxxx
SENTRY_AUTH_TOKEN=xxxxx
```

## Project Structure

```
agent-bot/
├── integrations/
│   ├── packages/           # Shared libraries (DRY principle)
│   │   ├── shared/        # Common utilities
│   │   ├── github_client/ # GitHub API client
│   │   ├── jira_client/   # Jira API client
│   │   ├── slack_client/  # Slack API client
│   │   └── sentry_client/ # Sentry API client
│   ├── api/               # API services (thin wrappers)
│   └── mcp-servers/       # MCP protocol servers
├── api-gateway/           # Webhook receiver (port 8000)
├── agent-container/       # Task executor with CLI runners
├── dashboard-api-container/  # Analytics API (port 8090)
├── external-dashboard/    # React UI (port 3005)
├── knowledge-graph/       # Rust-based graph (port 4000)
├── tests/
│   ├── unit/             # Fast unit tests (<5s)
│   ├── integration/      # Service integration tests
│   └── e2e/              # End-to-end tests
├── docker-compose.yml    # Main infrastructure
├── Makefile             # Development commands
└── .env.example         # Environment template
```

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Coverage report
make coverage
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
mypy .
```

### File Size Enforcement

Maximum 300 lines per Python file (pre-commit hook):

```bash
# Check file sizes
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print $1, $2}'
```

### Docker Operations

```bash
# Build containers
make build

# Start services
make up

# Stop services
make down

# Restart services
make restart

# View logs
make logs

# Follow logs
make logs-follow

# Clean up
make clean
```

### Database Operations

```bash
# Create migration
make db-migrate message="Add new table"

# Apply migrations
make db-upgrade

# Rollback migration
make db-downgrade

# Open database shell
make db-shell
```

## Code Quality Standards

**Strict enforcement for all code:**

1. **File Size**: Maximum 300 lines per file
2. **Type Safety**: NO `any` types, use `ConfigDict(strict=True)`
3. **Logging**: Structured logging only (no comments in code)
4. **Async**: Always use async/await for I/O operations
5. **Testing**: Fast (<5s per file), no flaky tests, no real network calls

## Monitoring & Health Checks

### Health Endpoints

```bash
# API Gateway
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics
```

### Redis CLI

```bash
make redis-cli
```

### Database Shell

```bash
make db-shell
```

## Troubleshooting

### Services Not Starting

```bash
# Check Docker status
docker-compose ps

# Check Redis
make redis-cli
PING  # Should return PONG

# View logs
make logs
```

### Tests Failing

```bash
# Check file sizes
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'

# Run type checking
mypy . --strict

# Verbose test output
pytest -v --tb=long
```

## Contributing

1. Follow the 300-line file size limit
2. Use Pydantic `strict=True` for all models
3. Write fast, deterministic tests
4. Use structured logging (no print statements)
5. Always use async/await for I/O operations

## License

MIT

## Support

For issues and feature requests, please open a GitHub issue.
