# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Production-ready AI agent systems monorepo with **five complete implementations** demonstrating different approaches to building autonomous AI agents for code management, bug fixing, and development automation.

**Technology Stack**: Python 3.11+, FastAPI, Docker, PostgreSQL/Redis, AWS Bedrock, Claude CLI

## System Comparison

| System | LLM Provider | Best For | Monthly Cost |
|--------|--------------|----------|--------------|
| `single-agent-system/` | AWS Bedrock | Local dev & testing | $40 |
| `multiple-agents-system/` | AWS Bedrock | AWS production at scale | $356 |
| `claude-code-cli/` ⭐ | Claude Teams | Enterprise production | $1,100 |
| `claude-code-cli-poc/` | Claude Teams | Quick POC & demos | $100-$150 |
| `agent-bot/` | Claude/Cursor CLI | Production microservices | Variable |

**⭐ Recommended**: `claude-code-cli/` for new production deployments (highest success rate at 75%)

## Key Commands

### Development Setup

```bash
# Single Agent System
cd single-agent-system
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
python cli.py run --description "Fix authentication bug"

# Multiple Agents System (AWS)
cd multiple-agents-system
uv venv && source .venv/bin/activate
uv pip install -e .
python cli.py run --ticket PROJ-123

# Claude Code CLI (Production)
cd claude-code-cli
./scripts/setup-local.sh
cd infrastructure/docker
docker-compose up -d

# Agent Bot (Microservices) - Multi-CLI Support
cd agent-bot
make init

# Start with Claude CLI (default)
make cli-up PROVIDER=claude SCALE=1

# Or start with Cursor CLI
make cli-up PROVIDER=cursor SCALE=1

# Or start all services
make up
```

### Agent Bot CLI Commands

```bash
cd agent-bot

# CLI Agent Management
make cli-up PROVIDER=claude SCALE=3    # Start Claude CLI (3 instances)
make cli-up PROVIDER=cursor SCALE=2    # Start Cursor CLI (2 instances)
make cli-logs PROVIDER=claude          # View logs
make cli-status PROVIDER=claude        # Check status
make cli-down PROVIDER=claude          # Stop

# All Services
make up                                # Start all services
make down                              # Stop all services
make health                            # Check service health
```

### Testing

```bash
# Agent Bot
cd agent-bot
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-cli          # Test CLI in container
make coverage          # Coverage report

# Other Systems
pytest                 # Run all tests
pytest -v             # Verbose output
pytest tests/unit/    # Unit tests only
```

### Code Quality

```bash
# Agent Bot (automated via pre-commit hooks)
make format           # Auto-format code
make lint            # Run linting
mypy .               # Type checking

# Check file sizes (300 line limit)
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print $1, $2}'
```

### Database Operations (Agent Bot)

```bash
make db-migrate message="Add new table"  # Create migration
make db-upgrade                          # Apply migrations
make db-downgrade                        # Rollback
make db-shell                            # Open database shell
```

### Docker Operations

```bash
# Agent Bot
make build            # Build containers
make up              # Start all services
make down            # Stop services
make restart         # Restart services
make logs            # View logs
make logs-follow     # Follow logs

# Claude Code CLI
cd infrastructure/docker
docker-compose build
docker-compose up -d
docker-compose logs -f
```

## Architecture Patterns

### 1. Single Agent System (Local Development)
- **Pattern**: Monolithic orchestration with AWS Bedrock
- **Location**: `single-agent-system/`
- **Key Files**:
  - `agents/` - Agent implementations (discovery, planning, execution)
  - `services/llm_service.py` - AWS Bedrock integration
  - `cli.py` - Command-line interface

### 2. Multiple Agents System (AWS Production)
- **Pattern**: Distributed agents using AWS Step Functions + Lambda
- **Location**: `multiple-agents-system/`
- **Key Files**:
  - `agents/` - Specialized agent implementations
  - `lambda/` - AWS Lambda handlers
  - `infrastructure/terraform/` - Infrastructure as code

### 3. Claude Code CLI (Enterprise Production) ⭐
- **Pattern**: Two-agent system with official MCP servers
- **Location**: `claude-code-cli/`
- **Key Files**:
  - `agents/planning-agent/` - Discovery + planning agent
  - `agents/executor-agent/` - Code execution agent
  - `services/webhook-server/` - FastAPI webhook receiver
  - `infrastructure/kubernetes/` - K8s deployment configs

### 4. Agent Bot (Production Microservices)
- **Pattern**: Modular microservices with webhook-driven orchestration
- **Location**: `agent-bot/`
- **Key Components**:
  - `api-gateway/` - Port 8080 - Webhook receiver
  - `agent-container/` - Task processor with CLI runners
  - `integrations/packages/` - Shared API clients (DRY principle)
  - `integrations/mcp-servers/` - MCP protocol servers
  - `dashboard-api-container/` - Port 8090 - Analytics

### 5. Claude Code Agent (Self-Managing System)
- **Pattern**: Brain orchestrator with specialized workflow agents
- **Location**: `claude-code-agent/`
- **Key Features**:
  - Brain agent routes tasks to 13 specialized agents
  - Persistent conversations with context awareness
  - Automatic response posting to GitHub/Jira/Slack
  - Human approval workflow for code changes
  - Self-improvement loop after task completion

## Critical Development Rules (Agent Bot)

**STRICT ENFORCEMENT** - Must be followed for all agent-bot code:

### File Size Limits
- **Maximum 300 lines per file** (enforced)
- Split into modules: `constants.py`, `models.py`, `exceptions.py`, `core.py`
- Check: `find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'`

### Type Safety
- **NO `any` types EVER**
- Always use `ConfigDict(strict=True)` in Pydantic models
- Explicit types for all function signatures
- Use `Literal` for enums

### Code Style
- **NO comments in code** - Self-explanatory code only
- Use descriptive variable/function names
- Extract complex logic into named functions
- Only docstrings for public APIs

### Testing Requirements
- Tests MUST pass gracefully
- Tests MUST run fast (< 5 seconds per file)
- NO flaky tests, NO real network calls
- Use `pytest-asyncio` for async code

### Async/Await
- ALWAYS use async/await for I/O operations
- Use `httpx.AsyncClient`, NOT `requests`
- Use `asyncio.gather()` for parallel operations

### Structured Logging
```python
# Good ✅
logger.info("task_started", task_id=task_id, user_id=user_id)

# Bad ❌
logger.info(f"Task {task_id} started")
```

## Common Development Workflows

### Adding a New Agent (Claude Code Agent)
1. Create agent file: `.claude/agents/{name}.md`
2. Define trigger, flow, and response posting logic
3. Add required skills in `.claude/skills/`
4. Brain automatically discovers and delegates to new agent

### Creating a New Microservice (Agent Bot)
1. Follow monorepo structure in `agent-bot/integrations/`
2. Create shared client in `packages/{service}_client/`
3. Build MCP server in `mcp-servers/{service}/`
4. Build REST API in `api/{service}/`
5. Services communicate via API/Queue only (NO direct imports)

### Implementing a New Workflow (All Systems)
1. **Discovery Phase**: Use discovery skills to find relevant repositories/files
2. **Planning Phase**: Create detailed implementation plan (PLAN.md)
3. **Execution Phase**: Follow TDD workflow (Red → Green → Refactor)
4. **Verification Phase**: Run tests (unit → integration → E2E)
5. **Approval Phase**: Human approval before merging (GitHub: `@agent approve`)

## TDD Workflow (All Systems)

Standard Test-Driven Development approach:

1. **Red**: Write failing test
2. **Green**: Implement minimal code to pass
3. **Refactor**: Clean up while keeping tests green
4. **Resilience**: Test error handling
5. **Acceptance**: Test user acceptance criteria
6. **Regression**: Ensure no old bugs reappear
7. **E2E**: End-to-end validation

## Webhook Integration

All systems support webhooks from:

| Provider | Trigger | Action |
|----------|---------|--------|
| **Jira** | Ticket with `AI-Fix` label | Start discovery & planning |
| **GitHub** | PR comment `@agent approve` | Execute implementation |
| **Sentry** | New error alert | Create Jira ticket |
| **Slack** | `/agent` command | Various agent actions |

### Webhook Endpoints (Agent Bot)
- `POST /webhooks/github` - GitHub events (port 8080)
- `POST /webhooks/jira` - Jira events (port 8080)
- `POST /webhooks/slack` - Slack events (port 8080)
- `POST /webhooks/sentry` - Sentry events (port 8080)

## Environment Configuration

### Required Environment Variables (Example: Agent Bot)
```bash
# Database
POSTGRES_URL=postgresql://user:pass@localhost:5432/agentbot
REDIS_URL=redis://localhost:6379/0

# CLI Configuration
CLI_RUNNER_TYPE=claude  # or 'cursor'

# API Keys (stored in .env, NOT in code)
GITHUB_TOKEN=ghp_xxx
JIRA_API_TOKEN=xxx
SLACK_BOT_TOKEN=xoxb-xxx
SENTRY_AUTH_TOKEN=xxx

# AWS (for Bedrock systems)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

## Monitoring & Observability (Agent Bot)

### Prometheus Metrics
- Access: `http://localhost:8080/metrics`
- Key metrics: `webhook_requests_total`, `task_processing_duration_seconds`, `tasks_in_queue`

### Dashboard Analytics
- Access: `http://localhost:8090/api/v1/dashboard/analytics`
- Logs: `http://localhost:8090/api/v1/dashboard/tasks/{task_id}/logs`

### Health Checks
```bash
curl http://localhost:8080/health      # API Gateway
curl http://localhost:8081/health      # GitHub Service
curl http://localhost:8090/health      # Dashboard API
```

## Project Structure Deep Dive

### Agent Bot (Microservices)
```
agent-bot/
├── api-gateway/           # Webhook receiver (< 100ms response)
│   └── core/             # Queue management, validation
├── agent-container/      # Task executor with CLI runners
│   ├── core/             # CLI runner, streaming logger
│   ├── adapters/         # Queue adapters (Redis)
│   └── ports/            # Interfaces (protocol-based)
├── integrations/         # DRY monorepo for external services
│   ├── packages/         # Shared clients (single source of truth)
│   ├── mcp-servers/      # MCP protocol implementations
│   └── api/              # REST API implementations
└── dashboard-api-container/  # Analytics & monitoring
```

### Claude Code Agent (Self-Managing)
```
claude-code-agent/
├── .claude/
│   ├── agents/           # 13 specialized agents (brain, planning, executor, etc.)
│   ├── skills/           # Reusable capabilities (github, jira, slack ops)
│   ├── memory/           # Learning & pattern recognition
│   └── CLAUDE.md         # Brain orchestrator configuration
├── api/                  # FastAPI routes
│   └── webhooks/         # Static & dynamic webhook handlers
├── core/                 # Core logic (CLI runner, config)
├── workers/              # Background task workers
└── services/dashboard-v2/  # React-based monitoring UI
```

## Cost Analysis & ROI

Based on real-world usage (see `COST-ANALYSIS-REALISTIC.md` for details):

| System | Monthly Cost | Tasks/Month | Success Rate | Net Value | Best For |
|--------|-------------|-------------|--------------|-----------|----------|
| Single Agent | $40 | 77 | 50% | $4,640 | Local dev |
| Multiple Agents | $356 | 385 | 55% | $25,084 | AWS production |
| CLI POC | $100 | 65 | 75% | $5,780 | Quick POC |
| **CLI Production** ⭐ | $1,100 | 580 | **75%** | **$51,100** | Enterprise |

**Key Insight**: Claude Code CLI has 2x higher success rate (75% vs 50-55%) due to official tool support and better agentic capabilities.

## Testing Strategy

### Unit Tests
- **Location**: `{service}/tests/test_*.py`
- **Requirements**: Fast (< 5s), no network calls, 100% type coverage
- **Run**: `pytest tests/unit/ -v`

### Integration Tests
- **Location**: `tests/integration/`
- **Requirements**: Test service interactions, use mocks for external APIs
- **Run**: `pytest -m integration`

### E2E Tests
- **Location**: `tests/e2e/`
- **Requirements**: Complete workflow validation
- **Run**: `pytest -m e2e`

## Migration Paths

### POC to Production (Recommended)
1. **Week 1-2**: Deploy `claude-code-cli-poc/` → Validate approach (< 2 days setup)
2. **Week 3-4**: Move to `claude-code-cli/` locally → Full feature testing
3. **Week 5-6**: Deploy to staging → Load testing with 500+ tasks
4. **Week 7+**: Production rollout → Scale to 50+ developers

### AWS-Only Path
1. Start with `single-agent-system/` → Learn concepts (1-2 hours setup)
2. Deploy `multiple-agents-system/` → Production on AWS (3-4 weeks)

## Documentation Structure

- **Root README.md** - High-level overview of all systems
- **System-specific README.md** - Individual system documentation
- **ARCHITECTURE.md files** - Detailed architecture documentation
- **docs/** - Comprehensive guides (POC, AWS implementation)
- **.claude/** - AI agent configurations (agent-bot, claude-code-agent)

## Git Workflow

### Commit Message Format
```
<type>: <subject>

<detailed description>

https://claude.ai/code/session_<session_id>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Branch Strategy
- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `refactor/*` - Code improvements

## Troubleshooting

### Agent Bot Services Not Starting
1. Check Docker: `docker-compose ps`
2. Check Redis: `make redis-cli` → `PING`
3. View logs: `make logs`
4. Health check: `./scripts/test-cli.sh health`

### Tests Failing
1. Check file sizes: `find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'`
2. Check types: `mypy . --strict`
3. Run tests with verbose: `pytest -v --tb=long`

### Database Issues
1. Check migrations: `make db-upgrade`
2. Open DB shell: `make db-shell`
3. Check schema: `.tables`, `SELECT * FROM tasks LIMIT 5;`

## Security Best Practices

- Store secrets in environment variables ONLY
- Use HMAC signature validation for webhooks
- Validate all user inputs with Pydantic `strict=True`
- Use prepared statements for SQL
- Enable audit logging in production
- Use IAM roles with least-privilege access (AWS systems)

## Key Differences Between Systems

**Single vs Multiple Agents**:
- Single: In-memory state, local orchestration
- Multiple: DynamoDB state, AWS Step Functions orchestration

**Custom Agents vs Claude Code CLI**:
- Custom: Lower success rate (50-55%), requires development effort
- Claude CLI: Higher success rate (75%), official tool support, faster setup

**Agent Bot vs Others**:
- Agent Bot: Microservices architecture, multi-CLI support (Claude + Cursor)
- Others: Monolithic or two-agent architectures

## Performance Optimization

### Agent Bot
- Use connection pooling for HTTP clients
- Async I/O for all network calls
- Redis for caching
- Use `asyncio.Semaphore` for rate limiting

### AWS Systems
- Enable prompt caching (saves ~75% on repeated prompts)
- Use Lambda provisioned concurrency for critical paths
- Implement circuit breakers for external APIs

## Additional Resources

- [Complete Architecture Design](./docs/ai-agent-production-system-v4.md)
- [AWS Implementation Guide](./docs/AWS-AGENTCORE-PRODUCTION-IMPLEMENTATION.md)
- [POC Implementation Guide](./docs/poc-implementation-guide.md)
- [Agent Bot Setup Guide](./agent-bot/docs/SETUP.md)
- [Agent Bot Testing Guide](./agent-bot/docs/TESTING.md)
