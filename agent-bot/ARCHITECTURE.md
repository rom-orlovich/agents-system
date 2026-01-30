# Agent Bot System - Architecture Documentation

## Overview

The Agent Bot System is a production-ready microservices architecture for AI agent orchestration with webhook-driven task management. The system follows strict architectural principles from the production PRD:

- **Standalone Components**: Each service is independent with no shared code
- **TDD Approach**: All business logic implemented with test-first development
- **Strict Type Safety**: No `any` types, comprehensive Pydantic validation
- **Self-Explanatory Code**: No comments, clear naming and modular structure
- **Dependency Injection**: Container-based dependency management

## System Architecture

### Components

```
agent-bot/
├── api-gateway/              # Webhook receiver and task queue (Port 8080)
├── github-service/           # GitHub API microservice (Port 8081)
├── jira-service/            # Jira API microservice (Port 8082)
├── slack-service/           # Slack API microservice (Port 8083)
├── sentry-service/          # Sentry API microservice (Port 8084)
├── dashboard-api-container/ # Dashboard API (Port 8090)
├── agent-container/         # AI agent execution
├── docker-compose.yml       # Container orchestration
└── Makefile                 # Build and test commands
```

### Data Flow

1. **Webhook Reception** (API Gateway)
   - Receives webhooks from GitHub/Jira/Slack/Sentry
   - Validates payload with Pydantic schemas
   - Creates task with unique task_id
   - Initializes centralized TaskLogger
   - Enqueues task to Redis queue

2. **Task Processing** (Agent Container)
   - Worker dequeues task from Redis
   - Accesses TaskLogger via task_id
   - Executes CLI runner (modular/extensible)
   - Logs agent output to centralized logger
   - Calls microservices via HTTP APIs

3. **External Service Integration** (Microservices)
   - Each service is standalone Docker container
   - GitHub/Jira/Slack/Sentry operations
   - Secure API key management
   - Comprehensive error handling

## Architecture Principles

### 1. No Shared Code

Components communicate **ONLY** via:
- HTTP REST APIs (synchronous)
- Redis Queue (asynchronous)
- API Contracts (Pydantic models)

**NO** shared Python packages or modules between components.

### 2. Strict Type Safety

```python
from pydantic import BaseModel, Field, ConfigDict

class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str = Field(..., min_length=1)
    input_message: str = Field(..., min_length=1)
    agent_type: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
```

- NO `any` types
- NO `!!` (force unwrapping)
- Explicit Optional handling with type guards
- Comprehensive Field validation

### 3. Task Flow Logging

Centralized logging system tracks complete task lifecycle:

```
/data/logs/tasks/{task_id}/
├── metadata.json              # Task metadata
├── 01-input.json              # Task input
├── 02-webhook-flow.jsonl      # Webhook events (API Gateway)
├── 03-queue-flow.jsonl        # Queue events (API Gateway → Agent)
├── 04-agent-output.jsonl      # Agent output (Agent Container)
├── 05-microservices-flow.jsonl # Microservice calls
└── 06-final-result.json       # Final result and metrics
```

**Centralization**: TaskLogger initialized in API Gateway, accessed by all services via `task_id`.

### 4. Modular CLI Runner

The Agent Container uses an extensible CLI runner design:

```python
from typing import Protocol

class CLIRunner(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...
```

Can be extended with new CLI agent types without modifying other components.

## Component Details

### API Gateway

**Purpose**: Webhook reception and task queue management

**Key Files**:
- `webhooks/receiver.py` - Webhook processing with validation
- `queue/redis_queue.py` - Redis-based task queue
- `core/task_logger.py` - Centralized task logger
- `core/models.py` - Pydantic schemas

**Endpoints**:
- `POST /webhooks/github` - GitHub webhook
- `POST /webhooks/jira` - Jira webhook
- `POST /webhooks/slack` - Slack webhook
- `POST /webhooks/sentry` - Sentry webhook
- `GET /health` - Health check

### GitHub Service

**Purpose**: GitHub API integration

**Key Files**:
- `api/routes.py` - FastAPI routes with Swagger
- `api/models.py` - Strict Pydantic request/response models
- `client/github_client.py` - GitHub API client

**Endpoints**:
- `POST /api/v1/github/pr/{owner}/{repo}/{pr_number}/comment`
- `POST /api/v1/github/issue/{owner}/{repo}/{issue_number}/comment`
- `GET /api/v1/github/pr/{owner}/{repo}/{pr_number}`
- `GET /api/v1/github/issue/{owner}/{repo}/{issue_number}`
- `GET /health`

### Agent Container

**Purpose**: AI agent task execution

**Key Files**:
- `workers/task_worker.py` - Task processing worker
- `core/cli_runner/interface.py` - CLI runner protocol
- `core/cli_runner/claude_cli_runner.py` - Claude CLI implementation
- `core/task_logger.py` - Task logging (accesses centralized logger)

**Features**:
- Modular CLI runner (extensible)
- Dependency injection
- Microservice integration
- Task flow logging

## Testing

### TDD Approach

All components follow Test-Driven Development:

1. **RED**: Write failing test
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Improve while keeping tests green

### Test Commands

```bash
make test              # Run all tests
make test-gateway      # API Gateway tests
make test-github       # GitHub Service tests
make test-agent        # Agent Container tests
```

### Test Coverage

- Webhook flow testing (end-to-end)
- API contract testing
- Queue management testing
- Task logger testing
- CLI runner testing

## Deployment

### Local Development

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - GITHUB_TOKEN
# - JIRA_URL, JIRA_TOKEN
# - SLACK_TOKEN
# - SENTRY_DSN
# - ANTHROPIC_API_KEY

# Build and start services
make build
make up

# View logs
make logs
```

### Production Deployment

Each service can be deployed independently:

```bash
# Build specific service
docker build -t api-gateway ./api-gateway

# Deploy with orchestration
docker-compose up -d api-gateway

# Scale agent containers
docker-compose up -d --scale agent-container=5
```

## API Documentation

Swagger documentation available at:

- API Gateway: http://localhost:8080/docs
- GitHub Service: http://localhost:8081/docs
- Jira Service: http://localhost:8082/docs
- Slack Service: http://localhost:8083/docs
- Sentry Service: http://localhost:8084/docs

## Monitoring

### Health Checks

All services provide `/health` endpoint:

```bash
curl http://localhost:8080/health
```

### Task Logs

View task logs via Dashboard API:

```bash
curl http://localhost:8090/api/logs/tasks/{task_id}
```

## Development Guidelines

### Code Quality Standards

1. **No Comments**: Code must be self-explanatory
   - Clear, descriptive names
   - Well-structured organization
   - Explicit type annotations

2. **Modular Design**:
   - Single Responsibility Principle
   - Clear interfaces between modules
   - Easily extensible components

3. **Type Safety**:
   - Explicit types everywhere
   - No `any`, no `!!`
   - Proper optional handling

### Adding New Services

To add a new microservice:

1. Copy template from existing service (e.g., `github-service/`)
2. Update service name in `pyproject.toml`
3. Implement API routes with Pydantic models
4. Write tests first (TDD)
5. Add to `docker-compose.yml`
6. Update documentation

### Extending CLI Runner

To add new CLI agent type:

1. Implement `CLIRunner` protocol
2. Create new class in `core/cli_runner/`
3. Write tests for new runner
4. Update `TaskProcessor` to use new runner

## Security

- API keys stored securely in environment variables
- Each microservice manages its own credentials
- Signature validation for webhooks (to be implemented)
- Rate limiting per service (to be implemented)

## Performance

- Async/await throughout for non-blocking I/O
- Redis queue for task distribution
- Independent scaling per component
- Connection pooling for databases

## Future Enhancements

- Knowledge Graph Service (planned, not implemented)
- MCP Server integration
- Advanced webhook signature validation
- Rate limiting and throttling
- Metrics and monitoring dashboards
- Multi-tenancy support

## References

- Production PRD: `claude-code-agent/docs/production-prd/`
- Architecture Migration: `production-prd/architecture-migration.md`
- Code Quality Standards: `production-prd/code-quality-standards.md`
- Standalone Components: `production-prd/standalone-components.md`
