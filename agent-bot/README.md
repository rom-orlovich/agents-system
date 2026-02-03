# Agent Bot

A fully containerized, scalable multi-agent system that processes webhooks from GitHub, Jira, Slack, and Sentry to autonomously handle development tasks. The system uses specialized AI agents orchestrated through CLI providers (Claude Code CLI or Cursor CLI) to execute tasks using Test-Driven Development (TDD) methodology.

## Overview

Agent Bot is a microservices-based platform that:

- **Receives webhooks** from external services (GitHub, Jira, Slack, Sentry)
- **Processes tasks** using specialized AI agents with TDD workflows
- **Executes code changes** through CLI providers (Claude or Cursor)
- **Posts responses** back to the originating service
- **Scales horizontally** to handle multiple concurrent tasks

## Architecture

The system consists of 18 containerized services:

| Service                | Port      | Purpose                                                        |
| ---------------------- | --------- | -------------------------------------------------------------- |
| **CLI (Agent Engine)** | 8080-8089 | Task execution (scalable)                                      |
| **API Gateway**        | 8000      | Webhook reception                                              |
| **Dashboard API**      | 5000      | Analytics & WebSocket hub                                      |
| **External Dashboard** | 3005      | React monitoring UI                                            |
| **OAuth Service**      | 8010      | Multi-provider OAuth flows                                     |
| **Task Logger**        | 8090      | Task output logging                                            |
| **Knowledge Graph**    | 4000      | Code entity indexing (Rust)                                    |
| **LlamaIndex Service** | 8100      | Semantic search & RAG (optional)                               |
| **Indexer Worker**     | 8004      | Data source indexing (optional)                                |
| **ChromaDB**           | 8000      | Vector database (optional)                                     |
| **MCP Servers**        | 9001-9005 | Tool interfaces (GitHub, Jira, Slack, Sentry, Knowledge Graph) |
| **API Services**       | 3001-3004 | REST API wrappers (GitHub, Jira, Slack, Sentry)                |
| **Redis**              | 6379      | Task queue & cache                                             |
| **PostgreSQL**         | 5432      | Persistent storage                                             |

### Key Components

- **13 Specialized Agents**: Brain, Planning, Executor, Verifier, GitHub handlers, Jira handler, Slack handler, and more
- **9 Reusable Skills**: Discovery, Testing, Code Refactoring, GitHub/Jira/Slack operations, etc.
- **MCP Protocol**: Model Context Protocol servers for external service integration
- **TDD Workflow**: Test-Driven Development methodology enforced throughout

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SYSTEM-ARCHITECTURE.md](docs/SYSTEM-ARCHITECTURE.md).

For integration and implementation details, see [docs/INTEGRATION-IMPLEMENTATION-PLAN.md](docs/INTEGRATION-IMPLEMENTATION-PLAN.md).

### Knowledge Layer (Optional)

The system includes an **optional knowledge layer** for enhanced context retrieval:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Optional Knowledge Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Indexer    │    │  LlamaIndex  │    │   ChromaDB   │       │
│  │   Worker     │───▶│   Service    │───▶│   (Vectors)  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                        ┌──────────────┐       │
│  │    OAuth     │                        │  Knowledge   │       │
│  │   Service    │                        │    Graph     │       │
│  └──────────────┘                        └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- **Graceful Degradation**: Agent Engine works without knowledge services
- **OAuth Integration**: Data sources use OAuth tokens for API access
- **Multi-Source Support**: GitHub, Jira, Confluence indexing
- **Runtime Toggle**: Enable/disable via API without restart

**Start with Knowledge Services:**

```bash
# Start with knowledge profile
docker-compose --profile knowledge up -d

# Or set environment variable
KNOWLEDGE_SERVICES_ENABLED=true make start
```

See [docs/SYSTEM-ARCHITECTURE.md](docs/SYSTEM-ARCHITECTURE.md) for complete knowledge layer documentation.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- API keys for external services (GitHub, Jira, Slack, Sentry)
- CLI provider credentials (Anthropic API key for Claude or Cursor API key)

### Initial Setup

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd agent-bot
   ```

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys and credentials
   ```

3. **Initialize the project**:

   ```bash
   make init
   ```

4. **Start the CLI agent engine**:

   ```bash
   # Start Claude CLI
   make cli-up PROVIDER=claude SCALE=1

   # Or start Cursor CLI
   make cli-up PROVIDER=cursor SCALE=1
   ```

5. **Start all services** (optional):

   ```bash
   make start
   ```

6. **Verify health**:
   ```bash
   make health
   curl http://localhost:8000/health
   ```

## Key Commands

### CLI Management

```bash
# Start Claude CLI
make cli-claude

# Start Cursor CLI
make cli-cursor

# Scale CLI instances
make cli-up PROVIDER=claude SCALE=3

# Stop CLI
make cli-down PROVIDER=claude

# View CLI logs
make cli-logs PROVIDER=claude

# Check CLI status
make cli-status PROVIDER=claude
```

### Service Management

```bash
# Start all services
make start

# Stop all services
make down

# View logs
docker-compose logs -f

# Check service health
make health
```

### Development

```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format

# Database migrations
make db-migrate MSG="description"
make db-upgrade
```

## Environment Variables

### Required Configuration

```bash
# CLI Provider (claude or cursor)
CLI_PROVIDER=claude

# Database
POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0

# External Service API Keys
GITHUB_TOKEN=ghp_xxx
JIRA_API_TOKEN=xxx
SLACK_BOT_TOKEN=xoxb-xxx
SENTRY_DSN=https://xxx@sentry.io/xxx

# Webhook Secrets
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx

# CLI Provider Credentials
ANTHROPIC_API_KEY=sk-ant-xxx  # For Claude
CURSOR_API_KEY=xxx            # For Cursor
```

See `.env.example` for the complete configuration template. For detailed environment variable documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#environment-variables).

## Project Structure

```
agent-bot/
├── agent-engine/          # CLI task execution engine
├── api-gateway/           # Webhook reception
├── api-services/          # REST API wrappers
├── dashboard-api/         # Analytics & WebSocket hub
├── external-dashboard/    # React monitoring UI
├── mcp-servers/          # MCP protocol servers
├── oauth-service/         # OAuth flows
├── task-logger/          # Task output logging
├── knowledge-graph/      # Code entity indexing
├── llamaindex-service/   # Semantic search (optional)
├── indexer-worker/       # Data source indexing (optional)
├── docs/                 # Documentation
├── docker-compose.yml     # Main orchestration
├── Makefile              # Development commands
└── .env.example          # Environment template
```

Each service directory contains its own README with service-specific documentation. See the [Related Documentation](#related-documentation) section below for links.

## Development Guidelines

### Critical Rules

**STRICT ENFORCEMENT** - Must be followed for all code:

1. **File Size Limits**: Maximum 300 lines per file

   - Split into: `constants.py`, `models.py`, `exceptions.py`, `core.py`

2. **Type Safety**: NO `any` types EVER

   - Always use `ConfigDict(strict=True)` in Pydantic models
   - Explicit types for all function signatures

3. **Code Style**: NO comments in code

   - Self-explanatory code only
   - Use descriptive variable/function names
   - Only docstrings for public APIs

4. **Testing**: Tests MUST pass gracefully and run fast (< 5 seconds per file)

   - NO flaky tests, NO real network calls
   - Use `pytest-asyncio` for async code

5. **Async/Await**: ALWAYS use async/await for I/O operations

   - Use `httpx.AsyncClient`, NOT `requests`
   - Use `asyncio.gather()` for parallel operations

6. **Structured Logging**:
   ```python
   logger.info("task_started", task_id=task_id, user_id=user_id)
   ```

### TDD Workflow

The project follows Test-Driven Development:

1. **RED**: Write failing test
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

See [CLAUDE.md](CLAUDE.md) for complete development rules. For TDD methodology details, see [docs/INTEGRATION-IMPLEMENTATION-PLAN.md](docs/INTEGRATION-IMPLEMENTATION-PLAN.md).

## Health Checks

```bash
# API Gateway
curl http://localhost:8000/health

# Agent Engine
curl http://localhost:8080/health

# Dashboard API
curl http://localhost:5000/health

# OAuth Service
curl http://localhost:8010/health

# Task Logger
curl http://localhost:8090/health

# Knowledge Graph
curl http://localhost:4000/health
```

## Scaling

The system supports horizontal scaling:

```bash
# Scale CLI workers
make cli-up PROVIDER=claude SCALE=5

# Scale specific service
docker-compose up -d --scale cli=5 cli
```

Each replica independently consumes from the same Redis queue. For scaling strategies and deployment details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#deployment).

## Security Model

- **Credential Isolation**: API keys only stored in API service containers
- **Webhook Validation**: HMAC-SHA256 signature validation for all webhooks
- **Loop Prevention**: Agent-posted content tracked to prevent infinite loops
- **No Direct Imports**: Services communicate via API/Queue only

For detailed security architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#security-model).

## Monitoring

- **Real-time Updates**: WebSocket connections for live task status
- **Task Logging**: All task output captured to files
- **Analytics Dashboard**: React UI at `http://localhost:3005`
- **Structured Logging**: JSON-formatted logs throughout

## Related Documentation

### Core Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete system architecture, data flow, service interactions, and deployment details
- **[docs/SYSTEM-ARCHITECTURE.md](docs/SYSTEM-ARCHITECTURE.md)** - Detailed system architecture with diagrams, layers, and data flows
- **[docs/INTEGRATION-IMPLEMENTATION-PLAN.md](docs/INTEGRATION-IMPLEMENTATION-PLAN.md)** - Integration guide and TDD implementation plan
- **[CLAUDE.md](CLAUDE.md)** - Development rules, conventions, and coding standards

### Service Documentation

#### Core Services

- **[agent-engine/README.md](agent-engine/README.md)** - Agent Engine service details, CLI providers, and agent orchestration
- **[api-gateway/README.md](api-gateway/README.md)** - Webhook reception and validation
- **[dashboard-api/README.md](dashboard-api/README.md)** - Analytics API and WebSocket hub
- **[external-dashboard/README.md](external-dashboard/README.md)** - React monitoring UI

#### Integration Services

- **[api-services/README.md](api-services/README.md)** - REST API wrappers overview
  - [api-services/github-api/README.md](api-services/github-api/README.md) - GitHub API service
  - [api-services/jira-api/README.md](api-services/jira-api/README.md) - Jira API service
- **[mcp-servers/README.md](mcp-servers/README.md)** - MCP protocol servers overview
  - [mcp-servers/jira-mcp/README.md](mcp-servers/jira-mcp/README.md) - Jira MCP server
  - [mcp-servers/slack-mcp/README.md](mcp-servers/slack-mcp/README.md) - Slack MCP server
  - [mcp-servers/sentry-mcp/README.md](mcp-servers/sentry-mcp/README.md) - Sentry MCP server
  - [mcp-servers/knowledge-graph-mcp/README.md](mcp-servers/knowledge-graph-mcp/README.md) - Knowledge Graph MCP server

#### Supporting Services

- **[oauth-service/README.md](oauth-service/README.md)** - OAuth flows and multi-provider authentication
- **[oauth-service/CLAUDE.md](oauth-service/CLAUDE.md)** - OAuth service architecture and integration guide
- **[task-logger/README.md](task-logger/README.md)** - Task output logging and capture
- **[knowledge-graph/README.md](knowledge-graph/README.md)** - Code entity indexing and graph database

#### Knowledge Layer (Optional)

- **[llamaindex-service/README.md](llamaindex-service/README.md)** - Semantic search and RAG service
- **[indexer-worker/README.md](indexer-worker/README.md)** - Data source indexing worker
- **[agent-engine/CLAUDE.md](agent-engine/CLAUDE.md)** - Agent engine architecture and knowledge integration

## License

[Add your license information here]

## Contributing

[Add contributing guidelines here]
