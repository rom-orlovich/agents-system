# Architecture Migration Plan

## Executive Summary

This plan outlines the migration from the current monolithic architecture to a modular, scalable microservices architecture with the following independent containers:

## Key Architectural Decisions

### 1. Microservices Architecture - Standalone Components

- **CRITICAL**: ALL external API calls (GitHub, Jira, Slack, Sentry) MUST go through respective microservice containers
- **Each component is STANDALONE and INDEPENDENT**:
  - Own Dockerfile, main.py, requirements.txt, pyproject.toml
  - Own dependencies (no shared libraries)
  - Own database (eventually - can start shared, migrate later)
  - Own configuration
  - Can be deployed independently
- **Communication ONLY via Queue or API**:
  - No direct code dependencies between components
  - Components communicate via HTTP APIs or message queues
  - No shared code/libraries (except API contracts via OpenAPI/Swagger)
- **Self-contained**: Each component manages its own dependencies and resources
- **Scalable**: Each component can scale independently based on load

**See `standalone-components.md`** for detailed architecture and migration path.

### 2. Python-Based with pip Dependencies

- All services use Python 3.11+
- All services use `requirements.txt` for pip dependencies
- **REQUIRED**: All services must have `pyproject.toml` for modern Python project configuration
- Consistent dependency management across all containers

**Language Analysis**: See `language-recommendations.md` for detailed analysis. **Recommendation: All Python initially** for consistency, type safety (Pydantic), and team velocity. Consider Rust for Knowledge Graph API if performance becomes bottleneck.

### 3. Strict Type Safety & Code Quality

- **NO `Any` types** - all types must be explicit and well-defined
- **NO `!!` (force unwrapping)** - all optional values must be handled explicitly with type guards
- **NO comments** - code must be self-explanatory through clear naming and structure
- **Strict Pydantic validation**: `model_config = ConfigDict(strict=True)` on all models
- **Comprehensive Field validation**: Use `Field()` with constraints (min_length, max_length, gt, lt, etc.)
- **Modular design**: Clear separation of concerns, easily extensible/replaceable components
- **Production-ready**: Clean, well-structured code with clear logic flow

**See `code-quality-standards.md`** for detailed examples and guidelines.

### 4. TDD & Testing Requirements

- **TDD for Business Logic**: Write tests FIRST for all business and requirements logic
- **Webhook Flow Testing**: Complete end-to-end tests for each webhook provider (GitHub, Jira, Slack, Sentry)
- **Test Webhook Process**: Verify entire webhook flow works correctly (reception → validation → processing → response)
- **Test-Driven Development**: RED → GREEN → REFACTOR cycle for all features
- **Integration Tests**: Test interactions between services
- **E2E Tests**: Test complete user workflows

### 5. Production-Ready Services

- Comprehensive Swagger/OpenAPI documentation (auto-generated from Pydantic)
- Proper error handling with HTTP status codes
- Health check endpoints (`/health`)
- Structured logging with structlog
- Metrics and monitoring endpoints
- Request timeouts and retry logic
- **Self-explanatory code**: No comments needed - code speaks for itself
- **Modular architecture**: Components easily extensible and replaceable

### 6. CLI Runner Extensibility

- **Modular CLI Runner**: Easily extensible to support different CLI agents
- **Replaceable Implementation**: Can swap CLI runner without affecting other components
- **Interface-Based Design**: Abstract base class/interface for CLI runners
- **Plugin Architecture**: Support for multiple CLI agent types

### 7. Split External Container

- **Microservices**: GitHub Service, Jira Service, Slack Service, Sentry Service (each is separate Docker container)
- **Dashboard API Container**: Statistics, logs, webhook management API for React dashboard

### 8. Knowledge Graph - Future Only

- Knowledge Graph service is **NOT implemented now**
- Marked as FUTURE - focus on other containers first

## Current Architecture Analysis

**Strengths:**

- Well-structured FastAPI application with clear separation of concerns
- Comprehensive test coverage (unit, integration, E2E)
- Robust Pydantic models enforcing business logic (Pydantic 2.5+)
- Redis + SQLite dual storage for queue and persistence
- Webhook system with static (hard-coded) and dynamic (database-driven) routes
- Multi-agent system with Brain orchestrator
- Python-based with pip/requirements.txt dependency management

**Pain Points:**

- Single monolithic container - difficult to scale individual components
- Webhook handling and agent execution tightly coupled
- Dashboard, API, and task worker all in one service
- Cannot independently scale agent workers vs. webhook receivers
- Mixed concerns: public-facing features with internal agent logic

## Proposed Architecture Benefits

1. **Independent Scaling**: Scale agent workers without scaling webhook receivers
2. **Service Isolation**: Replace agent container without affecting external services
3. **Clear Boundaries**: Separate public-facing features from internal agent logic
4. **Development Flexibility**: Teams can work on different containers independently
5. **Deployment Options**: Deploy containers on different infrastructure (K8s, serverless, etc.)
6. **Centralized API Management**: All external service calls (GitHub, Jira, Slack, Sentry) go through Services API Container
7. **API Key Security**: API keys stored securely in Services Container, not distributed across services
8. **Strict Type Safety**: All services use Pydantic models with strict validation and comprehensive Swagger documentation
9. **Production Ready**: All services designed for production with proper error handling, logging, and monitoring

---

## Phase 1: Foundation & Preparation (Week 1-2)

### 1.1 Create New Directory Structure

```
agent-system/
├── docker-compose.yml              # Orchestrates all containers
├── .env.example                    # Environment template
├── Makefile                        # Common operations
├── README.md                       # Architecture overview
├── claude.md                       # Root configuration (global rules, commands, agents, hooks, webhooks)
│
├── agent-container/                # Agent Container
│   ├── Dockerfile
│   ├── main.py                     # FastAPI app for internal dashboard
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── config/
│   ├── claude.md                   # Agent-specific configuration
│   ├── .claude/
│   │   ├── rules/                  # Execution rules
│   │   ├── skills/                 # Skills
│   │   ├── agents/                 # Agent definitions
│   │   ├── commands/
│   │   └── hooks/
│   ├── core/                       # Core logic
│   │   ├── cli_runner/             # Modular CLI runner (extensible)
│   │   │   ├── __init__.py
│   │   │   ├── interface.py        # CLIRunner protocol/interface
│   │   │   ├── claude_cli_runner.py # Claude CLI implementation
│   │   │   └── base_runner.py       # Base class with common logic
│   │   ├── task_processor.py       # Task processing logic
│   │   ├── dashboard_api.py        # Internal dashboard API
│   │   ├── services_client.py      # Client for microservices
│   │   └── task_logger.py           # Task logging system
│   ├── workers/                    # Task workers
│   │   └── task_worker.py
│   ├── tmp/                        # Cloned repositories
│   ├── logs/                       # Task logs directory
│   │   └── tasks/                  # Per-task logs
│   └── tests/
│
├── github-service/                  # GitHub Microservice (Separate Docker Container)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI GitHub service API with Swagger
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── api/                        # GitHub API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI routes
│   │   ├── models.py               # Pydantic request/response models
│   │   └── schemas.py              # Strict Pydantic schemas
│   ├── client/                     # GitHub API client logic
│   │   ├── __init__.py
│   │   ├── base_client.py          # Base client with auth, retry, error handling
│   │   └── github_client.py        # GitHub client implementation
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── credentials_manager.py  # Secure API key storage/retrieval
│   │   └── settings.py             # Pydantic settings
│   ├── storage/                    # Database for credentials/state
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   └── repository.py           # Repository pattern
│   ├── core/                       # Core utilities
│   │   └── task_logger.py          # Task logging system (for microservice calls)
│   └── tests/
│
├── jira-service/                    # Jira Microservice (Separate Docker Container)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI Jira service API with Swagger
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── api/                        # Jira API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI routes
│   │   ├── models.py               # Pydantic request/response models
│   │   └── schemas.py              # Strict Pydantic schemas
│   ├── client/                     # Jira API client logic
│   │   ├── __init__.py
│   │   ├── base_client.py          # Base client with auth, retry, error handling
│   │   └── jira_client.py          # Jira client implementation
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── credentials_manager.py  # Secure API key storage/retrieval
│   │   └── settings.py             # Pydantic settings
│   ├── storage/                    # Database for credentials/state
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   └── repository.py           # Repository pattern
│   └── tests/
│
├── slack-service/                   # Slack Microservice (Separate Docker Container)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI Slack service API with Swagger
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── api/                        # Slack API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI routes
│   │   ├── models.py               # Pydantic request/response models
│   │   └── schemas.py              # Strict Pydantic schemas
│   ├── client/                     # Slack API client logic
│   │   ├── __init__.py
│   │   ├── base_client.py          # Base client with auth, retry, error handling
│   │   └── slack_client.py         # Slack client implementation
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── credentials_manager.py  # Secure API key storage/retrieval
│   │   └── settings.py             # Pydantic settings
│   ├── storage/                    # Database for credentials/state
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   └── repository.py           # Repository pattern
│   └── tests/
│
├── sentry-service/                  # Sentry Microservice (Separate Docker Container)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI Sentry service API with Swagger
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── api/                        # Sentry API endpoints
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI routes
│   │   ├── models.py               # Pydantic request/response models
│   │   └── schemas.py              # Strict Pydantic schemas
│   ├── client/                     # Sentry API client logic
│   │   ├── __init__.py
│   │   ├── base_client.py          # Base client with auth, retry, error handling
│   │   └── sentry_client.py        # Sentry client implementation
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── credentials_manager.py  # Secure API key storage/retrieval
│   │   └── settings.py             # Pydantic settings
│   ├── storage/                    # Database for credentials/state
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   └── repository.py           # Repository pattern
│   └── tests/
│
├── dashboard-api-container/        # Dashboard API Container
│   ├── Dockerfile
│   ├── main.py                     # FastAPI app for dashboard API
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── api/                        # Dashboard API endpoints
│   │   ├── __init__.py
│   │   ├── analytics.py            # Analytics endpoints
│   │   ├── costs.py                # Cost tracking endpoints
│   │   ├── logs.py                 # Log viewing endpoints (NEW: Task log viewer)
│   │   ├── chat.py                 # Chat history endpoints
│   │   ├── webhooks_management.py  # Webhook management endpoints
│   │   └── models.py               # Pydantic request/response models
│   ├── dashboard/                  # React dashboard (v2) frontend
│   │   ├── src/
│   │   │   ├── features/
│   │   │   │   ├── overview/
│   │   │   │   ├── analytics/
│   │   │   │   ├── ledger/
│   │   │   │   ├── webhooks/
│   │   │   │   ├── chat/
│   │   │   │   ├── logs/           # NEW: Task log viewer UI
│   │   │   │   └── registry/
│   │   │   ├── components/
│   │   │   └── layouts/
│   │   └── package.json
│   ├── storage/                    # Database management
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   └── repository.py           # Repository pattern
│   └── tests/
│
├── api-gateway/                    # API Gateway (must work!)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI webhook receiver
│   ├── requirements.txt            # Python dependencies (pip)
│   ├── pyproject.toml              # REQUIRED: modern Python project config
│   ├── webhooks/                   # Webhook routes
│   │   ├── __init__.py
│   │   ├── receiver.py             # Generic webhook receiver
│   │   ├── validator.py            # Signature validation
│   │   └── router.py               # Route to queue
│   ├── queue/                      # Task queue management
│   │   ├── __init__.py
│   │   └── redis_queue.py
│   ├── core/                       # Core utilities
│   │   └── task_logger.py          # Task logging system
│   ├── logs/                       # Task logs directory
│   │   └── tasks/                  # Per-task logs
│   └── tests/
│
└── knowledge-graph/                # Knowledge Graph Service (FUTURE - NOT NOW)
    ├── Dockerfile
    ├── main.py                     # FastAPI knowledge graph API
    ├── requirements.txt            # Python dependencies (pip)
    ├── pyproject.toml              # REQUIRED: modern Python project config
    ├── engine/                     # Graph processing
    │   ├── processor.py
    │   └── relationships.py
    ├── storage/                    # Graph storage
    │   └── graph_db.py
    └── tests/
```

### 1.2 Requirements.txt Structure

**Goal**: Ensure all containers use pip-based dependency management like the current project.

**Example requirements.txt for all containers**:

```txt
# Core FastAPI and Pydantic
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# HTTP clients
httpx>=0.26.0

# Database
sqlalchemy>=2.0.0
aiosqlite>=0.19.0  # or asyncpg for PostgreSQL

# Redis
redis>=5.0.0

# Logging
structlog>=24.1.0

# Utilities
python-multipart>=0.0.6
pyyaml>=6.0.1
```

**Note**: Each container may have additional service-specific dependencies, but core dependencies should be consistent.

### 1.3 API Contracts & Standalone Models

**Goal**: Define API contracts (Pydantic models) for inter-component communication. Each component has its own models internally, but shares API contracts.

**Key Principle**: **NO shared code libraries** - only API contracts shared via:

- OpenAPI/Swagger documentation
- Pydantic model definitions (copied per component or generated from OpenAPI spec)
- Queue message schemas (JSON)

**Action Items**:

1. **Define API Contracts** (OpenAPI/Swagger specs):
   - GitHub Service API contract
   - Jira Service API contract
   - Slack Service API contract
   - Sentry Service API contract
   - Agent Container API contract
   - Dashboard API contract
   - API Gateway webhook contract

2. **Each Component Has Own Models**:
   - Internal models for database (SQLAlchemy)
   - API request/response models (Pydantic) - can be generated from OpenAPI spec
   - Queue message models (Pydantic)

3. **API Contract Versioning**:
   - Version APIs (e.g., `/api/v1/github/...`)
   - Maintain backward compatibility
   - Deprecation strategy

**Example: API Contract Definition**:

```python
# api-contracts/github-service/v1/models.py
# This file defines the API contract - can be copied to each component or generated

from pydantic import BaseModel, Field, ConfigDict

class PostPRCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    comment: str = Field(..., min_length=1, max_length=65536)

class PostPRCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    success: bool
    comment_id: int | None
    message: str
    error: str | None
```

**Component Implementation**:

```python
# github-service/api/models.py
# Component's own copy of API contract models
from pydantic import BaseModel, Field, ConfigDict

class PostPRCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    comment: str = Field(..., min_length=1, max_length=65536)

class PostPRCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    success: bool
    comment_id: int | None
    message: str
    error: str | None

# github-service/storage/models.py
# Component's own internal database models
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GitHubCredentialDB(Base):
    __tablename__ = "github_credentials"
    id = Column(Integer, primary_key=True)
    api_key = Column(String, nullable=False)
```

**Tests to Write First**:

```python
# api-contracts/tests/test_api_contracts.py
def test_github_service_api_contract():
    """Test GitHub Service API contract is well-defined"""

def test_api_contract_versioning():
    """Test API contracts support versioning"""

def test_queue_message_schemas():
    """Test queue message schemas are well-defined"""

def test_api_contract_compatibility():
    """Test API contracts maintain backward compatibility"""
```

### 1.4 Task Logging System - Centralized in API Gateway

**Goal**: Implement comprehensive task flow logging system with **centralized task logger initialization** in API Gateway. The API Gateway creates and manages the task logger, and all other services access it via `task_id`.

**Critical Requirements**:

- **Centralized Initialization**: Task logger is created in API Gateway when webhook is received
- **Early Task ID Generation**: `task_id` is generated immediately upon webhook reception
- **Shared Access**: All services (Agent Container, Microservices) access the same task logger using `task_id`
- **Structured Logging**: Use `structlog` for all services
- **Task Flow Tracking**: Track complete flow from webhook → API Gateway → Queue → Agent Container → Microservices
- **Correlation IDs**: Use `task_id` and `flow_id` to correlate logs across services
- **JSONL Format**: Store streaming logs in JSONL format for efficient querying
- **Non-blocking**: Logging failures should not block task execution
- **Shared Storage**: Logs stored in shared volume accessible by all containers

**Log Structure** (per task):

```
/data/logs/tasks/{task_id}/
├── metadata.json              # Task metadata (static)
├── 01-input.json              # Task input (static)
├── 02-webhook-flow.jsonl      # Webhook events stream (API Gateway)
├── 03-queue-flow.jsonl        # Queue events stream (API Gateway → Agent)
├── 04-agent-output.jsonl       # Agent output stream (Agent Container)
├── 05-microservices-flow.jsonl # Microservice calls stream (GitHub/Jira/Slack/Sentry)
└── 06-final-result.json        # Final result and metrics (static)
```

**Logging Stages**:

1. **Webhook Flow** (API Gateway):
   - `received`: Webhook received
   - `validation`: Signature validation
   - `parsing`: Payload parsing
   - `command_matching`: Command matching
   - `immediate_response`: Immediate response sent
   - `task_created`: Task created in database
   - `queue_push`: Task enqueued

2. **Queue Flow** (API Gateway → Agent Container):
   - `queued`: Task in queue
   - `dequeued`: Task dequeued by worker
   - `worker_assigned`: Worker assigned task

3. **Agent Output** (Agent Container):
   - `task_started`: Task execution started
   - `thinking`: Agent thinking output
   - `tool_call`: Tool call made
   - `tool_result`: Tool result received
   - `message`: Agent message output
   - `error`: Error occurred

4. **Microservices Flow** (GitHub/Jira/Slack/Sentry Services):
   - `service_call`: Service API called
   - `service_request`: Request details
   - `service_response`: Response received
   - `service_error`: Service error occurred

5. **Final Result**:
   - `completed`: Task completed successfully
   - `failed`: Task failed
   - `metrics`: Cost, tokens, duration

**Implementation**:

**Centralized Task Logger** (created in API Gateway, accessed by all services):

```python
# shared/task_logger.py (shared across containers)
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import json
from datetime import datetime, timezone
import os

class TaskLogger:
    """Centralized structured logger for task execution across microservices.

    The TaskLogger is initialized in API Gateway when webhook is received.
    All other services access the same logger instance using task_id.
    """

    _instances: Dict[str, "TaskLogger"] = {}  # Cache for task logger instances

    def __init__(self, task_id: str, logs_base_dir: Optional[Path] = None):
        """Initialize TaskLogger for a specific task.

        Args:
            task_id: Unique identifier for the task (generated in API Gateway)
            logs_base_dir: Base directory for logs (defaults to env var or /data/logs/tasks)
        """
        self.task_id = task_id
        if logs_base_dir is None:
            logs_base_dir = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
        self.logs_base_dir = Path(logs_base_dir)
        self._log_dir = self.logs_base_dir / task_id
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(task_id=task_id)

    @classmethod
    def get_or_create(cls, task_id: str, logs_base_dir: Optional[Path] = None) -> "TaskLogger":
        """Get existing TaskLogger instance or create new one.

        This allows all services to access the same logger instance.
        """
        if task_id not in cls._instances:
            cls._instances[task_id] = cls(task_id, logs_base_dir)
        return cls._instances[task_id]

    def write_metadata(self, data: Dict[str, Any]) -> None:
        """Write task metadata to metadata.json."""
        metadata_file = self._log_dir / "metadata.json"
        self._safe_write_json(metadata_file, data)

    def write_input(self, data: Dict[str, Any]) -> None:
        """Write task input to 01-input.json."""
        input_file = self._log_dir / "01-input.json"
        self._safe_write_json(input_file, data)

    def log_webhook_event(self, stage: str, **data):
        """Log webhook processing event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "task_id": self.task_id,
            **data
        }
        self._append_jsonl("02-webhook-flow.jsonl", event)
        self.logger.info("webhook_event", stage=stage, **data)

    def log_queue_event(self, stage: str, **data):
        """Log queue processing event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "task_id": self.task_id,
            **data
        }
        self._append_jsonl("03-queue-flow.jsonl", event)
        self.logger.info("queue_event", stage=stage, **data)

    def log_agent_output(self, output_type: str, **data):
        """Log agent output."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": output_type,
            "task_id": self.task_id,
            **data
        }
        self._append_jsonl("04-agent-output.jsonl", event)
        self.logger.info("agent_output", output_type=output_type, **data)

    def log_microservice_call(self, service: str, stage: str, **data):
        """Log microservice API call."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": service,
            "stage": stage,
            "task_id": self.task_id,
            **data
        }
        self._append_jsonl("05-microservices-flow.jsonl", event)
        self.logger.info("microservice_call", service=service, stage=stage, **data)

    def write_final_result(self, data: Dict[str, Any]) -> None:
        """Write final task result to 06-final-result.json."""
        result_file = self._log_dir / "06-final-result.json"
        self._safe_write_json(result_file, data)

    def _safe_write_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Safely write JSON file atomically."""
        try:
            import tempfile
            fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.rename(temp_path, file_path)
            except:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
        except Exception as e:
            self.logger.error("task_logger_write_failed", file=str(file_path), error=str(e))
            # Don't raise - logging failures should not block execution

    def _append_jsonl(self, filename: str, data: Dict[str, Any]):
        """Append JSON line to file."""
        try:
            file_path = self._log_dir / filename
            json_line = json.dumps(data) + "\n"
            with open(file_path, "a") as f:
                f.write(json_line)
        except Exception as e:
            self.logger.error("task_logger_append_failed", file=filename, error=str(e))
            # Don't raise - logging failures should not block execution
```

**Integration Points**:

- **API Gateway**: **CENTRALIZED** - Creates TaskLogger when webhook received, logs webhook events, queue events
- **Agent Container**: Accesses TaskLogger via `task_id`, logs agent output, microservice calls
- **Microservices**: Can access TaskLogger via `task_id` (optional - logs can also be written by Agent Container)
- **Dashboard API Container**: Provide log viewing API

**Centralized Flow**:

1. **API Gateway** receives webhook → Generates `task_id` → Creates `TaskLogger(task_id)`
2. **API Gateway** logs all webhook processing stages
3. **API Gateway** includes `task_id` in task metadata when enqueueing
4. **Agent Container** receives task with `task_id` → Accesses `TaskLogger.get_or_create(task_id)`
5. **Agent Container** logs agent output and microservice calls
6. All logs written to shared volume `/data/logs/tasks/{task_id}/`

**Configuration**:

```python
# config/settings.py (in each container)
task_logs_enabled: bool = True
task_logs_dir: Path = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
task_logs_retention_days: int = 30
```

**Key Points**:

1. **API Gateway is the CENTRAL point** for TaskLogger initialization
2. **task_id is generated IMMEDIATELY** when webhook is received
3. **All services access the same logger** using `TaskLogger.get_or_create(task_id)`
4. **task_id is passed** through task metadata, queue, and all service calls
5. **Shared volume** ensures all containers can write to the same log directory
6. **Non-blocking** - logging failures never block task execution

### 1.5 Standalone Component Architecture

**Goal**: Each component is completely standalone and independent, communicating only via queue or API.

**Key Principles**:

1. **No Shared Code**: Each component has its own codebase, no shared libraries
2. **API Contracts**: Components communicate via well-defined API contracts (Pydantic models)
3. **Queue-Based Communication**: Async communication via Redis queue
4. **Self-Contained Dependencies**: Each component manages its own dependencies
5. **Independent Deployment**: Each component can be deployed/updated independently

**Communication Patterns**:

- **Synchronous**: HTTP REST APIs (for request/response)
- **Asynchronous**: Redis Queue (for task processing)
- **Event-Driven**: WebSocket (for real-time updates, optional)

**Component Independence**:

```
Component A (API Gateway)
  ↓ HTTP API
Component B (GitHub Service)
  ↓ HTTP API
Component C (Agent Container)
  ↓ Redis Queue
Component D (Dashboard API)
```

**NO Direct Dependencies**:

- ❌ No shared Python packages between components
- ❌ No direct database connections between components
- ❌ No shared code files
- ✅ Only API contracts (Pydantic models) shared via API documentation
- ✅ Only queue messages (JSON) for async communication

### 1.6 Database Strategy - Standalone Per Component

**Goal**: Each component eventually has its own database for true independence.

**Phase 1: Shared Database (Initial Migration)**:

- All components connect to same PostgreSQL instance
- Simpler migration path
- Easy to debug during transition
- Shared volume for logs

**Phase 2: Separate Databases (Production)**:

- **Agent Container**: Own PostgreSQL database for task execution data, agent state
- **Dashboard API Container**: Own PostgreSQL database for analytics, logs, webhook configs
- **API Gateway**: Own PostgreSQL database for webhook events, queue metadata
- **GitHub Service**: Own PostgreSQL database for GitHub API credentials, service state
- **Jira Service**: Own PostgreSQL database for Jira API credentials, service state
- **Slack Service**: Own PostgreSQL database for Slack API credentials, service state
- **Sentry Service**: Own PostgreSQL database for Sentry API credentials, service state
- **Knowledge Graph**: Own database for entity relationships (FUTURE)

**Action Items**:

1. Design API contracts first (Pydantic models)
2. Create database access layer with repository pattern per component
3. Define clear data ownership boundaries
4. Create migration scripts for database separation
5. Implement API versioning for backward compatibility

**Graceful Degradation**:

Since components don't depend on each other, they must handle failures gracefully:

```python
# agent-container/core/services_client.py
class GitHubServiceClient:
    async def post_pr_comment(...) -> dict[str, str | int | bool]:
        try:
            response = await self.client.post(...)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error("github_service_unavailable", service_url=self.service_url)
            raise ServiceUnavailableError("GitHub service is temporarily unavailable")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                raise ServiceUnavailableError("GitHub service is overloaded")
            raise
```

**Benefits**:

- Components can start independently
- One component failure doesn't cascade
- Can update components without downtime
- Easy to test components in isolation

---

## Phase 2: API Gateway Container (Week 3-4)

### 2.1 Extract Webhook Routes

**Goal**: Move webhook reception logic to independent API Gateway.

**Current State**:

- Webhooks in `api/webhooks/github/routes.py`, `jira/routes.py`, `slack/routes.py`
- Dynamic webhooks in `api/webhooks_dynamic.py`
- Validation in `api/webhooks/*/validation.py`

**New State**:

```
api-gateway/
├── webhooks/
│   ├── receiver.py              # Generic webhook receiver
│   ├── github/
│   │   ├── validator.py         # Signature validation
│   │   ├── parser.py            # Payload parsing
│   │   └── metadata.py          # Extract routing metadata
│   ├── jira/
│   │   ├── validator.py
│   │   ├── parser.py
│   │   └── metadata.py
│   └── slack/
│       ├── validator.py
│       ├── parser.py
│       └── metadata.py
```

**TDD Approach**:

1. **Write tests first** (RED) - Test entire webhook flow:

```python
# api-gateway/tests/test_webhook_flow.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_github_webhook_complete_flow():
    """Test complete GitHub webhook flow: reception → validation → processing → response"""
    client = AsyncClient(base_url="http://test")

    payload = {
        "action": "created",
        "issue": {"number": 42, "body": "@agent analyze this"},
        "repository": {"full_name": "owner/repo"}
    }

    response = await client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "issues"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    task_id = response.json()["task_id"]
    assert task_id is not None

    task = await get_task_from_db(task_id)
    assert task.status == "QUEUED"
    assert task.assigned_agent is not None

@pytest.mark.asyncio
async def test_github_webhook_invalid_signature():
    """Test webhook rejection with invalid signature"""
    ...

@pytest.mark.asyncio
async def test_github_webhook_no_command_match():
    """Test webhook with no matching command returns 200 but no task created"""
    ...

@pytest.mark.asyncio
async def test_jira_webhook_complete_flow():
    """Test complete Jira webhook flow"""
    ...

@pytest.mark.asyncio
async def test_slack_webhook_complete_flow():
    """Test complete Slack webhook flow"""
    ...

def test_webhook_validation_logic():
    """Test webhook signature validation logic"""
    ...

def test_task_queue_enqueue():
    """Test task is enqueued to Redis correctly"""
    ...

def test_webhook_logging():
    """Test webhook events are logged correctly"""
    ...
```

2. **Implement** (GREEN):
   - Create `api-gateway/webhooks/receiver.py` with strict typing
   - Extract validation logic from current codebase
   - Implement task creation and queue insertion
   - Add comprehensive error handling
   - Ensure all types are explicit (no `Any`, no `!!`)

3. **Refactor**:
   - Remove duplication between GitHub/Jira/Slack validators
   - Extract common patterns
   - Ensure code is self-explanatory (no comments)

**Integration Points**:

- **Input**: HTTP POST from GitHub, Jira, Slack (external services)
- **Output**: Task enqueued to Redis Queue (async communication)
- **Dependencies**:
  - Redis (for queue - shared infrastructure)
  - PostgreSQL (own database - eventually separate per component)
  - NO direct dependencies on other components

**Standalone Requirements**:

- **No shared code**: API Gateway has its own codebase
- **API communication**: Calls microservices via HTTP API (not direct code)
- **Queue communication**: Enqueues tasks to Redis (async, no direct dependency)
- **Self-contained**: All dependencies in own requirements.txt
- **Independent deployment**: Can deploy without other components running

**Type Safety Requirements**:

- All function parameters and return types must be explicit
- No `Any` types allowed
- No `!!` (force unwrapping) - use proper type guards
- Use `Optional[T]` or `T | None` for nullable values
- Use type guards: `if value is not None:` before accessing optional values

**Logging Integration** (Centralized in API Gateway):

```python
# api-gateway/webhooks/receiver.py
from core.task_logger import TaskLogger
from pathlib import Path
import uuid
import os

async def receive_webhook(provider: str, request: Request):
    """Receive and process webhook - CENTRALIZED TASK LOGGER INITIALIZATION."""

    # STEP 1: Generate task_id IMMEDIATELY upon webhook reception
    task_id = f"task-{uuid.uuid4().hex[:12]}"

    # STEP 2: Create TaskLogger CENTRALLY in API Gateway
    logs_base_dir = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
    task_logger = TaskLogger.get_or_create(task_id, logs_base_dir)

    # STEP 3: Write initial metadata and input
    task_logger.write_metadata({
        "task_id": task_id,
        "source": "webhook",
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "initializing"
    })

    # Log webhook received
    task_logger.log_webhook_event(
        stage="received",
        provider=provider,
        event_type=extract_event_type(request),
        headers=dict(request.headers)
    )

    # Validate signature
    task_logger.log_webhook_event(stage="validation", status="started")
    if not await validate_signature(request, provider):
        task_logger.log_webhook_event(stage="validation", status="failed")
        raise HTTPException(status_code=401)
    task_logger.log_webhook_event(stage="validation", status="passed")

    # Parse payload
    task_logger.log_webhook_event(stage="parsing", status="started")
    payload = await request.json()
    task_logger.log_webhook_event(stage="parsing", status="completed", payload_size=len(str(payload)))

    # Write input
    task_logger.write_input({
        "message": extract_message(payload, provider),
        "source_metadata": {
            "provider": provider,
            "event_type": extract_event_type(request),
            **extract_source_metadata(payload, provider)
        }
    })

    # Match command
    task_logger.log_webhook_event(stage="command_matching", status="started")
    command = match_command(payload, provider)
    if command:
        task_logger.log_webhook_event(
            stage="command_matching",
            status="matched",
            command=command.name
        )
    else:
        task_logger.log_webhook_event(stage="command_matching", status="no_match")
        return Response(status_code=200)

    # Send immediate response
    task_logger.log_webhook_event(stage="immediate_response", status="started")
    await send_immediate_response(provider, payload, command)
    task_logger.log_webhook_event(stage="immediate_response", status="completed")

    # Create task (include task_id in task metadata)
    task_logger.log_webhook_event(stage="task_created", status="started")
    task = await create_task(payload, command, task_id=task_id)  # Pass task_id
    task_logger.log_webhook_event(
        stage="task_created",
        status="completed",
        task_id=task.task_id,
        agent=task.assigned_agent
    )

    # Update metadata with task details
    task_logger.write_metadata({
        "task_id": task_id,
        "source": "webhook",
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "assigned_agent": task.assigned_agent,
        "agent_type": task.agent_type
    })

    # Enqueue task (task_id is included in task object)
    task_logger.log_queue_event(stage="queue_push", status="started")
    await queue.enqueue(task.task_id)  # task_id passed to queue
    task_logger.log_queue_event(stage="queue_push", status="completed", queue_name="tasks")

    return Response(status_code=200)
```

### 2.2 Task Queue Management

**Goal**: Centralize task queue operations in API Gateway.

**Tests First**:

```python
# api-gateway/tests/test_queue.py
def test_task_enqueue_with_priority():
    """High-priority tasks should be processed first"""

def test_task_queue_load_balancing():
    """Tasks should be distributed across agent workers"""

def test_task_deduplication():
    """Duplicate tasks should not be enqueued"""
```

**Implementation**:

```python
# api-gateway/queue/redis_queue.py
class TaskQueue:
    async def enqueue(self, task: TaskDB, priority: int = 0):
        """Enqueue task with priority"""

    async def dequeue(self, worker_id: str) -> Optional[TaskDB]:
        """Dequeue task for specific worker"""
```

### 2.3 Backward Compatibility

**Goal**: Ensure current webhook endpoints continue to work during migration.

**Strategy**:

1. Run both old and new webhook endpoints simultaneously
2. Use feature flags to route traffic
3. Monitor metrics to ensure parity
4. Gradually shift traffic to new endpoints

**Tests**:

```python
# tests/integration/test_backward_compat.py
def test_old_github_webhook_still_works():
    """Old /webhooks/github endpoint should still work"""

def test_new_gateway_webhook_works():
    """New API Gateway endpoint should work"""
```

---

## Phase 3: Microservices Containers (Week 5-6) - CRITICAL: MUST WORK FIRST

### 3.1 Extract Service Clients to Independent Microservices (Each in Separate Docker Container)

**Goal**: Move ALL external service integrations to independent microservices. Each microservice (GitHub, Jira, Slack, Sentry) is its own Docker container. This is the SINGLE POINT OF ENTRY for all external API calls. Agents, API Gateway, and Dashboard API will all call these microservices.

**Critical Requirements**:

- **ALL** external API calls (POST, GET, PUT, DELETE, PATCH) must go through microservices
- Each microservice is a **separate Docker container** with its own Dockerfile
- API keys stored securely in each microservice's storage
- Strict Pydantic schemas for all requests/responses
- Comprehensive Swagger documentation
- Production-ready error handling, logging, monitoring
- **REQUIRED**: Each microservice must have `pyproject.toml`

**Current State**:

- `core/github_client.py` (608 lines)
- `core/jira_client.py` (336 lines)
- `core/slack_client.py` (325 lines)

**New State - Each Microservice is Separate Docker Container**:

```
github-service/                     # GitHub Microservice (Separate Docker Container)
├── Dockerfile
├── main.py                         # FastAPI GitHub service API with Swagger
├── requirements.txt                # Python dependencies (pip)
├── pyproject.toml                  # REQUIRED: modern Python project config
├── api/
│   ├── routes.py                   # FastAPI routes with Swagger
│   ├── models.py                   # Pydantic request/response models
│   └── schemas.py                  # Strict Pydantic schemas
├── client/
│   ├── base_client.py              # Base client with auth, retry, error handling
│   └── github_client.py            # GitHub client implementation
├── config/
│   ├── credentials_manager.py      # Secure API key storage/retrieval
│   └── settings.py                 # Pydantic settings
├── storage/
│   ├── models.py                   # SQLAlchemy models for credentials
│   └── repository.py                # Repository pattern
└── tests/

jira-service/                      # Jira Microservice (Separate Docker Container)
├── Dockerfile
├── main.py                         # FastAPI Jira service API with Swagger
├── requirements.txt
├── pyproject.toml                  # REQUIRED
├── api/
├── client/
├── config/
├── storage/
└── tests/

slack-service/                     # Slack Microservice (Separate Docker Container)
├── Dockerfile
├── main.py                         # FastAPI Slack service API with Swagger
├── requirements.txt
├── pyproject.toml                  # REQUIRED
├── api/
├── client/
├── config/
├── storage/
└── tests/

sentry-service/                    # Sentry Microservice (Separate Docker Container)
├── Dockerfile
├── main.py                         # FastAPI Sentry service API with Swagger
├── requirements.txt
├── pyproject.toml                  # REQUIRED
├── api/
├── client/
├── config/
├── storage/
└── tests/
```

**TDD Approach** (Example for GitHub Service):

1. **Write API tests first** (RED):

```python
# github-service/tests/test_github_api.py
from pydantic import ValidationError
import pytest

def test_post_pr_comment_success():
    """POST /api/github/pr/{owner}/{repo}/{pr_number}/comment - success"""
    # Test with valid Pydantic request model

def test_post_pr_comment_invalid_schema():
    """POST /api/github/pr/{owner}/{repo}/{pr_number}/comment - invalid schema"""
    # Test Pydantic validation rejects invalid data

def test_get_pr_details():
    """GET /api/github/pr/{owner}/{repo}/{pr_number} - success"""

def test_api_key_validation():
    """Verify API key validation for requests"""

def test_swagger_documentation():
    """Verify Swagger docs are generated correctly"""
```

2. **Implement with strict Pydantic schemas** (GREEN):

```python
# github-service/api/models.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class PostPRCommentRequest(BaseModel):
    """Request model for posting PR comment."""
    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "owner": "octocat",
                "repo": "Hello-World",
                "pr_number": 1,
                "comment": "Great work!"
            }
        }
    )

    owner: str = Field(..., description="Repository owner", min_length=1)
    repo: str = Field(..., description="Repository name", min_length=1)
    pr_number: int = Field(..., description="Pull request number", gt=0)
    comment: str = Field(..., description="Comment body", min_length=1, max_length=65536)

class PostPRCommentResponse(BaseModel):
    """Response model for posting PR comment."""
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: Optional[int] = None
    message: str
    error: Optional[str] = None

# github-service/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from api.models import PostPRCommentRequest, PostPRCommentResponse
from config.credentials_manager import get_github_credentials
from client.github_client import GitHubClient

router = APIRouter(
    prefix="/api/github",
    tags=["GitHub Service"],
    responses={404: {"description": "Not found"}}
)

@router.post(
    "/pr/{owner}/{repo}/{pr_number}/comment",
    response_model=PostPRCommentResponse,
    summary="Post comment to GitHub PR",
    description="Post a comment to a GitHub pull request. Requires valid GitHub API credentials.",
    responses={
        200: {"description": "Comment posted successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized - invalid API key"},
        404: {"description": "PR not found"},
        500: {"description": "Internal server error"}
    }
)
async def post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    request: PostPRCommentRequest,
    credentials = Depends(get_github_credentials)
) -> PostPRCommentResponse:
    """Post comment to GitHub PR with strict Pydantic validation."""
    try:
        client = GitHubClient(credentials)
        result = await client.post_pr_comment(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            comment=request.comment
        )
        return PostPRCommentResponse(
            success=True,
            comment_id=result.comment_id,
            message="Comment posted successfully"
        )
    except Exception as e:
        logger.error("Failed to post PR comment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post comment: {str(e)}"
        )
```

3. **Refactor**:
   - Extract common patterns
   - Improve error handling
   - Add retry logic
   - Enhance logging

**Integration Points** (All via API or Queue):

- **Agent Container** → Calls GitHub/Jira/Slack/Sentry microservices via HTTP API (no direct code dependency)
- **API Gateway** → May call microservices via HTTP API for webhook-related operations
- **Dashboard API Container** → Calls microservices via HTTP API for service status/metrics
- **Each Microservice** → Calls its respective external API (GitHub, Jira, Slack, Sentry) with stored credentials
- **Agent Container** → Receives tasks from Redis Queue (async, no direct dependency)

**Standalone Requirements**:

- **No shared code**: Each microservice has its own codebase
- **API communication**: All inter-component communication via HTTP REST APIs
- **Self-contained**: All dependencies in own requirements.txt
- **Independent deployment**: Can deploy/update without affecting other components
- **API versioning**: Support versioned APIs for backward compatibility

**Production Requirements**:

- Comprehensive error handling with proper HTTP status codes
- Request/response logging
- Rate limiting per service
- Health check endpoints
- Metrics/monitoring endpoints
- API key rotation support
- Request timeout handling
- Retry logic with exponential backoff

---

## Phase 4: Agent Container (Week 7-9)

### 4.1 Extract Core Agent Logic

**Goal**: Create isolated Agent Container with internal dashboard. **CRITICAL**: Agent Container must call microservices for ALL external API operations (GitHub, Jira, Slack, Sentry).

**Current Components to Extract**:

- `core/cli_runner.py` - Claude CLI executor (REFACTOR to be modular/extensible)
- `workers/task_worker.py` - Task processor
- `.claude/` directory - Agent configurations
- Internal dashboard API (subset of current dashboard)
- `core/github_client.py`, `core/jira_client.py`, `core/slack_client.py` - **REMOVE** (use microservices instead)

### 4.2 Modular CLI Runner Design

**Goal**: Create extensible, replaceable CLI runner that can support different CLI agents.

**Requirements**:

- **Interface-based design**: Abstract base class for CLI runners
- **Strict typing**: No `Any`, no `!!`, all types explicit
- **Modular**: Easy to extend with new CLI agent types
- **Replaceable**: Can swap implementation without affecting other components
- **Self-explanatory**: No comments, clear naming and structure
- **TDD**: Write tests first for CLI runner interface and implementations

**TDD Approach**:

1. **Write tests first** (RED):

```python
# agent-container/tests/test_cli_runner_interface.py
from abc import ABC, abstractmethod
from typing import Protocol
from pydantic import BaseModel

class CLIResult(BaseModel):
    success: bool
    output: str
    error: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int

class CLIRunner(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...

def test_cli_runner_interface():
    """Test that CLI runner interface is well-defined"""

def test_claude_cli_runner_implements_interface():
    """Test Claude CLI runner implements interface correctly"""

def test_cli_runner_can_be_replaced():
    """Test that CLI runner can be swapped without breaking code"""
```

2. **Implement interface** (GREEN):

```python
# agent-container/core/cli_runner/interface.py
from abc import ABC, abstractmethod
from typing import Protocol
from pydantic import BaseModel

class CLIResult(BaseModel):
    success: bool
    output: str
    error: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int

class CLIRunner(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...

# agent-container/core/cli_runner/claude_cli_runner.py
from core.cli_runner.interface import CLIRunner, CLIResult
import subprocess
from pathlib import Path

class ClaudeCLIRunner:
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        command = self._build_command(prompt, working_dir, model, agents)
        result = await self._run_command(command, working_dir)
        return self._parse_result(result)

    def _build_command(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> list[str]:
        ...

    async def _run_command(
        self,
        command: list[str],
        working_dir: str
    ) -> subprocess.CompletedProcess:
        ...

    def _parse_result(
        self,
        result: subprocess.CompletedProcess
    ) -> CLIResult:
        ...
```

3. **Refactor**: Extract common patterns, improve modularity

**Usage Example**:

```python
# agent-container/core/task_processor.py
from core.cli_runner.interface import CLIRunner
from core.cli_runner.claude_cli_runner import ClaudeCLIRunner

class TaskProcessor:
    def __init__(self, cli_runner: CLIRunner | None = None):
        self.cli_runner = cli_runner or ClaudeCLIRunner()

    async def process_task(self, task: TaskDB) -> TaskResult:
        result = await self.cli_runner.execute(
            prompt=task.input_message,
            working_dir=task.working_dir,
            model=task.model,
            agents=task.assigned_agents
        )
        return TaskResult.from_cli_result(result)
```

**New Structure**:

```
agent-container/
├── core/
│   ├── cli_runner.py           # Claude CLI executor (moved)
│   ├── task_processor.py       # Task processing logic
│   ├── dashboard_api.py        # Internal dashboard API
│   └── services_client.py      # Client for Services API Container (NEW)
├── workers/
│   └── task_worker.py          # Task worker (moved)
├── .claude/
│   ├── rules/                  # Execution rules
│   ├── skills/                 # Skills (moved)
│   ├── agents/                 # Agent definitions (moved)
│   ├── commands/
│   └── hooks/
└── dashboard/
    └── internal/               # Internal agent management UI
```

**Critical Changes**:

- **REMOVE** direct external API clients (github_client, jira_client, slack_client)
- **ADD** Services API Container client (`core/services_client.py`)
- All GitHub/Jira/Slack/Sentry operations go through Services API Container
- Skills that use external APIs must be updated to call Services API Container

**Services Client Example** (Agent Container - Standalone, communicates via API):

```python
# agent-container/core/services_client.py
# Standalone component - no shared code, communicates via HTTP API only
from httpx import AsyncClient
from pydantic import BaseModel
import structlog
from core.task_logger import TaskLogger
import os
from typing import Protocol

logger = structlog.get_logger()

class GitHubServiceClient:
    """Client for GitHub Service - communicates via HTTP API only."""

    def __init__(self, service_url: str, task_id: str | None = None):
        self.service_url = service_url
        self.client = AsyncClient(base_url=service_url, timeout=30.0)
        self.task_id = task_id
        self.task_logger = TaskLogger.get_or_create(task_id) if task_id else None

    async def post_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str
    ) -> dict[str, str | int | bool]:
        """Post comment via GitHub Service API - no direct code dependency."""
        if self.task_logger:
            self.task_logger.log_microservice_call(
                service="github",
                stage="service_call",
                endpoint=f"/api/v1/github/pr/{owner}/{repo}/{pr_number}/comment",
                method="POST"
            )

        try:
            response = await self.client.post(
                f"{self.service_url}/api/v1/github/pr/{owner}/{repo}/{pr_number}/comment",
                json={"comment": comment}
            )

            if self.task_logger:
                self.task_logger.log_microservice_call(
                    service="github",
                    stage="service_response",
                    status_code=response.status_code,
                    success=response.is_success
                )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            if self.task_logger:
                self.task_logger.log_microservice_call(
                    service="github",
                    stage="service_error",
                    error=str(e),
                    error_type=type(e).__name__
                )
            raise

class ServicesAPIClient:
    """Aggregated client for all microservices - standalone component."""

    def __init__(
        self,
        github_service_url: str,
        jira_service_url: str,
        slack_service_url: str,
        sentry_service_url: str,
        task_id: str | None = None
    ):
        self.github = GitHubServiceClient(github_service_url, task_id)
        self.jira = JiraServiceClient(jira_service_url, task_id)
        self.slack = SlackServiceClient(slack_service_url, task_id)
        self.sentry = SentryServiceClient(sentry_service_url, task_id)

    async def post_github_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str
    ) -> dict:
        """Post comment to GitHub PR via GitHub Service microservice."""
        github_service_url = os.getenv("GITHUB_SERVICE_URL", "http://github-service:8081")

        # Log microservice call using centralized logger
        if self.task_logger:
            self.task_logger.log_microservice_call(
                service="github",
                stage="service_call",
                endpoint=f"/api/github/pr/{owner}/{repo}/{pr_number}/comment",
                method="POST"
            )

        try:
            response = await self.client.post(
                f"{github_service_url}/api/github/pr/{owner}/{repo}/{pr_number}/comment",
                json={"comment": comment}
            )

            # Log response using centralized logger
            if self.task_logger:
                self.task_logger.log_microservice_call(
                    service="github",
                    stage="service_response",
                    status_code=response.status_code,
                    success=response.is_success
                )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Log error using centralized logger
            if self.task_logger:
                self.task_logger.log_microservice_call(
                    service="github",
                    stage="service_error",
                    error=str(e),
                    error_type=type(e).__name__
                )
            raise

# agent-container/workers/task_worker.py
from core.task_logger import TaskLogger

async def process_task(task_id: str):
    """Process task - accesses centralized TaskLogger."""
    # Access centralized TaskLogger created in API Gateway
    task_logger = TaskLogger.get_or_create(task_id)

    task_logger.log_agent_output("task_started", status="running")

    # ... process task ...

    task_logger.log_agent_output("thinking", content="Analyzing...")
    task_logger.log_agent_output("tool_call", tool="github", action="post_comment")

    # Use services client with task_id
    services_client = ServicesAPIClient(base_url="", task_id=task_id)
    await services_client.post_github_pr_comment(...)

    # ... complete task ...

    task_logger.write_final_result({
        "success": True,
        "result": "...",
        "metrics": {...}
    })
```

---

## Phase 5: Dashboard API Container (Week 10-12)

### 5.1 Dashboard API & Analytics

**Goal**: Move public-facing dashboard API to Dashboard API Container. This container provides APIs for the React dashboard frontend.

**Current Components**:

- `services/dashboard-v2/` - React dashboard (frontend)
- `api/analytics.py` - Analytics API
- `api/dashboard.py` - Dashboard API
- `api/webhook_status.py` - Webhook management API

**New Structure**:

```
dashboard-api-container/
├── api/
│   ├── analytics.py                # Analytics endpoints with Pydantic models
│   ├── costs.py                    # Cost tracking endpoints
│   ├── logs.py                     # Log viewing endpoints
│   ├── chat.py                     # Chat history endpoints
│   ├── webhooks_management.py      # Webhook management endpoints
│   └── models.py                   # All Pydantic request/response models
├── dashboard/                      # React dashboard frontend
│   └── src/
└── storage/                        # Database access
```

**Requirements**:

- All endpoints must use strict Pydantic models
- Comprehensive Swagger documentation
- Production-ready error handling
- Calls microservices for service-related data
- **Log viewing API**: Endpoint to view task logs (`/api/logs/tasks/{task_id}`)

**Log Viewing API Example**:

```python
# dashboard-api-container/api/logs.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Dict, Any
import json

router = APIRouter(prefix="/api/logs")

def read_json_file(file_path: Path) -> Dict[str, Any]:
    """Read JSON file."""
    if not file_path.exists():
        return {}
    with open(file_path) as f:
        return json.load(f)

def read_jsonl_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file."""
    if not file_path.exists():
        return []
    events = []
    with open(file_path) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events

@router.get("/tasks/{task_id}")
async def get_task_logs(task_id: str) -> Dict[str, Any]:
    """Get all logs for a task."""
    log_dir = Path("/data/logs/tasks") / task_id

    if not log_dir.exists():
        raise HTTPException(status_code=404, detail="Task logs not found")

    logs = {
        "task_id": task_id,
        "metadata": read_json_file(log_dir / "metadata.json"),
        "input": read_json_file(log_dir / "01-input.json"),
        "webhook_flow": read_jsonl_file(log_dir / "02-webhook-flow.jsonl"),
        "queue_flow": read_jsonl_file(log_dir / "03-queue-flow.jsonl"),
        "agent_output": read_jsonl_file(log_dir / "04-agent-output.jsonl"),
        "microservices_flow": read_jsonl_file(log_dir / "05-microservices-flow.jsonl"),
        "final_result": read_json_file(log_dir / "06-final-result.json")
    }

    return logs
```

---

## Phase 6: Knowledge Graph Service (FUTURE - NOT IMPLEMENTED NOW)

### 6.1 External Knowledge Graph API

**Status**: This service is planned for future implementation. Do not implement now.

**Goal**: Create external service for entity relationships and context storage.

**Features** (Future):

- Receive webhook events from API Gateway
- Process and store entity relationships (users, projects, issues, PRs)
- Provide context for agent tasks
- Query interface for agents

**Note**: This service will be implemented later. Focus on Services API Container, Dashboard API Container, API Gateway, and Agent Container first.

---

## Phase 7: Container Orchestration & Deployment (Week 15-16)

### 7.1 Docker Compose Configuration

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - agent-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: agent_system
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agent-network

  api-gateway:
    build: ./api-gateway
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - TASK_LOGS_DIR=/data/logs/tasks
      - GITHUB_SERVICE_URL=http://github-service:8081
      - JIRA_SERVICE_URL=http://jira-service:8082
      - SLACK_SERVICE_URL=http://slack-service:8083
      - SENTRY_SERVICE_URL=http://sentry-service:8084
    volumes:
      - task_logs:/data/logs/tasks
    depends_on:
      - redis
      - postgres
    networks:
      - agent-network
    restart: unless-stopped

  github-service:
    build: ./github-service
    ports:
      - "8081:8081"
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - REDIS_URL=redis://redis:6379/2
    depends_on:
      - postgres
      - redis
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    deploy:
      replicas: 1

  jira-service:
    build: ./jira-service
    ports:
      - "8082:8082"
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - REDIS_URL=redis://redis:6379/3
    depends_on:
      - postgres
      - redis
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  slack-service:
    build: ./slack-service
    ports:
      - "8083:8083"
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - REDIS_URL=redis://redis:6379/4
    depends_on:
      - postgres
      - redis
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  sentry-service:
    build: ./sentry-service
    ports:
      - "8084:8084"
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - REDIS_URL=redis://redis:6379/5
    depends_on:
      - postgres
      - redis
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  dashboard-api-container:
    build: ./dashboard-api-container
    ports:
      - "8090:8090"
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - GITHUB_SERVICE_URL=http://github-service:8081
      - JIRA_SERVICE_URL=http://jira-service:8082
      - SLACK_SERVICE_URL=http://slack-service:8083
      - SENTRY_SERVICE_URL=http://sentry-service:8084
      - TASK_LOGS_DIR=/data/logs/tasks
    volumes:
      - task_logs:/data/logs/tasks
    depends_on:
      - postgres
    networks:
      - agent-network
    restart: unless-stopped

  agent-container:
    build: ./agent-container
    environment:
      - GITHUB_SERVICE_URL=http://github-service:8081
      - JIRA_SERVICE_URL=http://jira-service:8082
      - SLACK_SERVICE_URL=http://slack-service:8083
      - SENTRY_SERVICE_URL=http://sentry-service:8084
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@postgres:5432/agent_system
      - REDIS_URL=redis://redis:6379/0
      - TASK_LOGS_DIR=/data/logs/tasks
    volumes:
      - agent_data:/data
      - task_logs:/data/logs/tasks
    depends_on:
      - redis
      - postgres
    networks:
      - agent-network
    deploy:
      replicas: 2
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  agent_data:
  task_logs: # Shared volume for task logs across containers

networks:
  agent-network:
    driver: bridge
```

---

## Dependencies Between Services

```mermaid
graph TB
    ExtServices[External Services<br/>GitHub, Jira, Slack, Sentry]
    Gateway[API Gateway]
    Queue[Task Queue<br/>Redis]
    GitHubService[GitHub Service<br/>Docker Container]
    JiraService[Jira Service<br/>Docker Container]
    SlackService[Slack Service<br/>Docker Container]
    SentryService[Sentry Service<br/>Docker Container]
    AgentContainer[Agent Container]
    DashboardAPI[Dashboard API Container]
    KnowledgeGraph[Knowledge Graph API<br/>FUTURE]
    Database[(Database<br/>PostgreSQL)]

    ExtServices -->|Webhooks| Gateway
    ExtServices -->|API Calls| GitHubService
    ExtServices -->|API Calls| JiraService
    ExtServices -->|API Calls| SlackService
    ExtServices -->|API Calls| SentryService
    Gateway -->|Enqueue Tasks| Queue
    Gateway -->|Forward Events| KnowledgeGraph
    Queue -->|Dequeue Tasks| AgentContainer
    AgentContainer -->|GitHub API Calls| GitHubService
    AgentContainer -->|Jira API Calls| JiraService
    AgentContainer -->|Slack API Calls| SlackService
    AgentContainer -->|Sentry API Calls| SentryService
    AgentContainer -->|Query Context| KnowledgeGraph
    DashboardAPI -->|Service Data| GitHubService
    DashboardAPI -->|Service Data| JiraService
    DashboardAPI -->|Service Data| SlackService
    DashboardAPI -->|Service Data| SentryService
    GitHubService -->|Call GitHub API| ExtServices
    JiraService -->|Call Jira API| ExtServices
    SlackService -->|Call Slack API| ExtServices
    SentryService -->|Call Sentry API| ExtServices
    DashboardAPI -->|Read Data| Database
    AgentContainer -->|Write Task Data| Database
    Gateway -->|Write Events| Database
    GitHubService -->|Store Credentials| Database
    JiraService -->|Store Credentials| Database
    SlackService -->|Store Credentials| Database
    SentryService -->|Store Credentials| Database
    KnowledgeGraph -->|Write Entities| Database
```

**Critical Flow**:

1. **ALL** external API calls (GitHub, Jira, Slack, Sentry) MUST go through respective microservice containers
2. Each microservice stores and manages its own API keys securely
3. Components communicate **ONLY via API or Queue** - no direct code dependencies
4. Each component is **STANDALONE** - manages own dependencies, can run independently
5. Each component can be deployed/updated **independently** without affecting others
6. Each component can be scaled **independently** based on its own load
7. Components depend only on infrastructure (Redis, PostgreSQL) - not on each other

---

## Critical Requirements for All Services

### Python & Dependencies

- **All services use Python 3.11+**
- **All services use `requirements.txt` for pip dependencies**
- **REQUIRED**: All services must have `pyproject.toml` for modern Python project configuration
- **Core dependencies**: FastAPI, Pydantic 2.5+, httpx, SQLAlchemy, Redis

### Pydantic & Type Safety

- **ALL request/response models must use Pydantic BaseModel**
- **Strict validation**: `model_config = ConfigDict(strict=True)` on all models
- **NO `Any` types** - all types must be explicit and well-defined
- **NO `!!` (force unwrapping)** - all optional values must be handled explicitly with proper type guards
- **Field validation**: Use `Field()` with constraints (min_length, max_length, gt, lt, etc.)
- **Comprehensive schemas**: Every API endpoint must have request/response models
- **Type guards**: Use `isinstance()` checks and type narrowing for optional values
- **Union types**: Explicitly define all possible types, never use `Any`

### Swagger/OpenAPI Documentation

- **All services must have comprehensive Swagger docs**
- **Auto-generated from Pydantic models**
- **Include descriptions, examples, and error responses**
- **Accessible at `/docs` endpoint**

### Code Quality Standards

- **NO comments**: Code must be self-explanatory through:
  - Clear, descriptive function/variable names
  - Well-structured code organization
  - Explicit type annotations
  - Clear logic flow
- **Modular design**:
  - Single Responsibility Principle
  - Clear interfaces between modules
  - Easily extensible and replaceable components
- **Production-ready**:
  - Clean, well-structured code
  - Clear logic flow
  - Proper error handling
  - No placeholders or TODOs

### TDD & Testing Requirements

- **TDD for Business Logic**: Write tests FIRST for all business and requirements logic
- **Webhook Flow Testing**: Complete end-to-end tests for each webhook provider
  - Test entire flow: reception → validation → command matching → task creation → queue → processing
  - Test error scenarios: invalid signatures, missing commands, API failures
  - Test edge cases: malformed payloads, rate limits, timeouts
- **Test-Driven Development**: RED → GREEN → REFACTOR cycle
- **Integration Tests**: Test interactions between services
- **E2E Tests**: Test complete user workflows

### Production Readiness

- **Error handling**: Proper HTTP status codes, error messages, logging
- **Health checks**: `/health` endpoint for all services
- **Logging**: Structured logging with structlog + TaskLogger for task flow tracking
- **Task Flow Tracking**: Complete task flow logging from webhook → queue → agent → microservices
- **Monitoring**: Metrics endpoints for monitoring
- **Security**: API key management, input validation, rate limiting
- **Retry logic**: Exponential backoff for external API calls
- **Timeouts**: Request timeouts for all external calls
- **Database**: Proper connection pooling, migrations

### Microservices Architecture - Standalone Components

- **Each component is STANDALONE**:
  - Own Dockerfile, codebase, dependencies
  - Own database (eventually - can start shared)
  - Own configuration
  - No shared code libraries
- **Communication ONLY via Queue or API**:
  - HTTP REST APIs for synchronous communication
  - Redis Queue for asynchronous task processing
  - WebSocket for real-time updates (optional)
  - NO direct code dependencies between components
- **API Contracts**:
  - Well-defined API contracts (OpenAPI/Swagger)
  - Versioned APIs (`/api/v1/...`)
  - Pydantic models for request/response validation
- **Independent Deployment**:
  - Each component can be deployed/updated independently
  - No downtime for other components when updating one
  - Can scale each component independently
- **Self-Contained**:
  - Each component manages its own dependencies
  - Each component has its own error handling, logging, monitoring
  - Each component can run standalone (with mocked dependencies for testing)

## Critical Files for Implementation

1. **`workers/task_worker.py`** - Core task processing logic
2. **`api/webhooks/github/routes.py`** - Webhook handling pattern
3. **`core/database/models.py`** - Database schema
4. **`core/github_client.py`** - Service client pattern (to be moved to Services API Container)
5. **`main.py`** - Application entry point
6. **`shared/machine_models.py`** - Pydantic models for shared types
7. **`github-service/api/routes.py`** - GitHub microservice routes (NEW)
8. **`github-service/api/models.py`** - GitHub Pydantic schemas (NEW)
9. **`agent-container/core/services_client.py`** - Microservices client (NEW)
10. **`api-gateway/core/task_logger.py`** - Task logging system (NEW - standalone implementation)
11. **`agent-container/core/task_logger.py`** - Task logging system (NEW - standalone implementation, same interface)
12. **`dashboard-api-container/api/logs.py`** - Log viewing API (NEW)
13. **`agent-container/core/cli_runner/interface.py`** - CLI runner interface (NEW - modular/extensible)
14. **`agent-container/core/cli_runner/claude_cli_runner.py`** - Claude CLI implementation (NEW)
15. **`code-quality-standards.md`** - Code quality standards and examples (NEW)
16. **`standalone-components.md`** - Standalone components architecture guide (NEW)

---

## Success Metrics

### Technical Metrics

- **Scalability**: Agent workers can scale independently
- **Performance**: Task processing latency ≤ current system
- **Reliability**: Service uptime ≥ 99.9%
- **Test Coverage**: Maintain ≥ 85% coverage

### Business Metrics

- **Deployment Flexibility**: Deploy containers independently
- **Development Velocity**: Teams work without conflicts
- **Cost Efficiency**: Optimize resource allocation per container

### Architecture Compliance

- **Standalone Components**: Each component is independent, manages own dependencies, communicates only via API/Queue
- **Centralized API Access**: 100% of external API calls go through microservices
- **Type Safety**: 100% Pydantic models, zero `Any` types, zero `!!` force unwrapping
- **Code Quality**: Self-explanatory code with no comments, modular and extensible
- **TDD Coverage**: All business logic and webhook flows have comprehensive tests
- **Documentation**: 100% API endpoints documented in Swagger
- **Production Ready**: All services pass health checks, have proper error handling, logging, monitoring
- **CLI Runner Extensibility**: CLI runner can be extended/replaced without affecting other components
- **Independent Deployment**: Components can be deployed/updated independently without affecting others
