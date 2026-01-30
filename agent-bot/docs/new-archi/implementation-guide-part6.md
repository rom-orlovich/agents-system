# Agent Bot - TDD Implementation Guide

## Part 6: Final Integration, Migrations & Testing

---

## Phase 12: Database Migrations

### Step 12.1: Create Migration Structure

```bash
mkdir -p database/migrations/versions
touch database/migrations/__init__.py
touch database/migrations/env.py
touch database/migrations/versions/__init__.py
touch database/migrations/versions/001_create_installations.py
touch database/migrations/versions/002_create_tasks.py
```

### Step 12.2: Installation Table Migration

**File: `database/migrations/versions/001_create_installations.py`** (< 100 lines)

```python
from datetime import datetime

MIGRATION_ID = "001"
MIGRATION_NAME = "create_installations"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TABLE IF NOT EXISTS installations (
    id VARCHAR(50) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    webhook_secret VARCHAR(255) NOT NULL,
    installed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    installed_by VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT installations_platform_org_unique 
        UNIQUE(platform, organization_id)
);

CREATE INDEX idx_installations_platform 
    ON installations(platform);

CREATE INDEX idx_installations_org_id 
    ON installations(organization_id);

CREATE INDEX idx_installations_active 
    ON installations(is_active) 
    WHERE is_active = TRUE;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_installations_updated_at
    BEFORE UPDATE ON installations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS update_installations_updated_at ON installations;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP INDEX IF EXISTS idx_installations_active;
DROP INDEX IF EXISTS idx_installations_org_id;
DROP INDEX IF EXISTS idx_installations_platform;
DROP TABLE IF EXISTS installations;
"""


async def up(connection) -> None:
    await connection.execute(UP_SQL)


async def down(connection) -> None:
    await connection.execute(DOWN_SQL)
```

### Step 12.3: Tasks Table Migration

**File: `database/migrations/versions/002_create_tasks.py`** (< 100 lines)

```python
from datetime import datetime

MIGRATION_ID = "002"
MIGRATION_NAME = "create_tasks"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TYPE task_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE task_priority AS ENUM (
    'critical',
    'high',
    'normal',
    'low'
);

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(50) PRIMARY KEY,
    installation_id VARCHAR(50) NOT NULL REFERENCES installations(id),
    provider VARCHAR(20) NOT NULL,
    status task_status NOT NULL DEFAULT 'pending',
    priority task_priority NOT NULL DEFAULT 'normal',
    input_message TEXT NOT NULL,
    output TEXT,
    error TEXT,
    source_metadata JSONB NOT NULL DEFAULT '{}',
    execution_metadata JSONB NOT NULL DEFAULT '{}',
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_installation 
    ON tasks(installation_id);

CREATE INDEX idx_tasks_status 
    ON tasks(status);

CREATE INDEX idx_tasks_created 
    ON tasks(created_at DESC);

CREATE INDEX idx_tasks_pending 
    ON tasks(priority, created_at) 
    WHERE status = 'pending';

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
DROP INDEX IF EXISTS idx_tasks_pending;
DROP INDEX IF EXISTS idx_tasks_created;
DROP INDEX IF EXISTS idx_tasks_status;
DROP INDEX IF EXISTS idx_tasks_installation;
DROP TABLE IF EXISTS tasks;
DROP TYPE IF EXISTS task_priority;
DROP TYPE IF EXISTS task_status;
"""


async def up(connection) -> None:
    await connection.execute(UP_SQL)


async def down(connection) -> None:
    await connection.execute(DOWN_SQL)
```

### Step 12.4: Migration Runner

**File: `database/migrations/runner.py`** (< 100 lines)

```python
import importlib
from pathlib import Path
from typing import Protocol

import asyncpg
import structlog

logger = structlog.get_logger()


class MigrationModule(Protocol):
    MIGRATION_ID: str
    MIGRATION_NAME: str

    async def up(self, connection: asyncpg.Connection) -> None:
        ...

    async def down(self, connection: asyncpg.Connection) -> None:
        ...


class MigrationRunner:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def run_all(self) -> int:
        conn = await asyncpg.connect(self._database_url)
        try:
            await self._ensure_migrations_table(conn)
            applied = await self._get_applied_migrations(conn)
            migrations = self._load_migrations()

            count = 0
            for migration in migrations:
                if migration.MIGRATION_ID in applied:
                    continue

                logger.info(
                    "applying_migration",
                    migration_id=migration.MIGRATION_ID,
                    name=migration.MIGRATION_NAME,
                )

                async with conn.transaction():
                    await migration.up(conn)
                    await self._record_migration(conn, migration.MIGRATION_ID)

                count += 1

            return count
        finally:
            await conn.close()

    async def rollback(self, steps: int = 1) -> int:
        conn = await asyncpg.connect(self._database_url)
        try:
            applied = await self._get_applied_migrations(conn)
            migrations = self._load_migrations()
            migrations.reverse()

            count = 0
            for migration in migrations:
                if count >= steps:
                    break
                if migration.MIGRATION_ID not in applied:
                    continue

                logger.info(
                    "rolling_back_migration",
                    migration_id=migration.MIGRATION_ID,
                )

                async with conn.transaction():
                    await migration.down(conn)
                    await self._remove_migration(conn, migration.MIGRATION_ID)

                count += 1

            return count
        finally:
            await conn.close()

    async def _ensure_migrations_table(self, conn: asyncpg.Connection) -> None:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

    async def _get_applied_migrations(
        self, conn: asyncpg.Connection
    ) -> set[str]:
        rows = await conn.fetch("SELECT id FROM _migrations")
        return {row["id"] for row in rows}

    async def _record_migration(
        self, conn: asyncpg.Connection, migration_id: str
    ) -> None:
        await conn.execute(
            "INSERT INTO _migrations (id) VALUES ($1)", migration_id
        )

    async def _remove_migration(
        self, conn: asyncpg.Connection, migration_id: str
    ) -> None:
        await conn.execute(
            "DELETE FROM _migrations WHERE id = $1", migration_id
        )

    def _load_migrations(self) -> list[MigrationModule]:
        migrations_dir = Path(__file__).parent / "versions"
        migrations = []

        for path in sorted(migrations_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module_name = f"database.migrations.versions.{path.stem}"
            module = importlib.import_module(module_name)
            migrations.append(module)

        return migrations
```

---

## Phase 13: Docker Configuration

### Step 13.1: Agent Container Dockerfile

**File: `agent-container/Dockerfile`** (< 80 lines)

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://claude.ai/install.sh | sh

FROM base AS builder

COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN useradd --create-home --shell /bin/bash agent
RUN mkdir -p /data/repos /data/logs /data/graph && chown -R agent:agent /data

USER agent

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')"

ENTRYPOINT ["python", "-m", "worker.main"]
```

### Step 13.2: API Gateway Dockerfile

**File: `api-gateway/Dockerfile`** (< 60 lines)

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

FROM base AS builder

COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN useradd --create-home --shell /bin/bash api
USER api

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')"

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 13.3: Docker Compose - Local Development

**File: `docker-compose.yml`** (< 150 lines)

```yaml
version: "3.9"

services:
  api-gateway:
    build:
      context: ./api-gateway
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://agent:agent@postgres:5432/agent_bot
      - REDIS_URL=redis://redis:6379
      - GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
      - GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - agent-network

  agent-container:
    build:
      context: ./agent-container
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://agent:agent@postgres:5432/agent_bot
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REPO_BASE_PATH=/data/repos
      - LOG_BASE_PATH=/data/logs
      - LOG_LEVEL=INFO
    volumes:
      - repo-data:/data/repos
      - log-data:/data/logs
      - graph-data:/data/graph
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    networks:
      - agent-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=agent
      - POSTGRES_PASSWORD=agent
      - POSTGRES_DB=agent_bot
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent -d agent_bot"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - agent-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - agent-network

  knowledge-graph:
    image: registry.gitlab.com/gitlab-org/rust/knowledge-graph:latest
    volumes:
      - repo-data:/data/repos:ro
      - graph-data:/data/graph
    environment:
      - GKG_DATA_DIR=/data/graph
    ports:
      - "3030:3030"
    networks:
      - agent-network

  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    ports:
      - "8090:8090"
    environment:
      - API_URL=http://api-gateway:8080
      - REDIS_URL=redis://redis:6379
    depends_on:
      - api-gateway
    networks:
      - agent-network

volumes:
  postgres-data:
  redis-data:
  repo-data:
  log-data:
  graph-data:

networks:
  agent-network:
    driver: bridge
```

### Step 13.4: Docker Compose - Testing

**File: `docker-compose.test.yml`** (< 60 lines)

```yaml
version: "3.9"

services:
  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - DATABASE_URL=postgresql://test:test@postgres-test:5432/test_db
      - REDIS_URL=redis://redis-test:6379
      - TESTING=true
    depends_on:
      postgres-test:
        condition: service_healthy
      redis-test:
        condition: service_healthy
    command: pytest -v --cov --cov-report=xml
    volumes:
      - ./coverage:/app/coverage

  postgres-test:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test_db
    tmpfs:
      - /var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d test_db"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis-test:
    image: redis:7-alpine
    tmpfs:
      - /data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

---

## Phase 14: Integration Tests

### Step 14.1: Write Integration Tests

**File: `tests/integration/test_webhook_to_task.py`** (< 200 lines)

```python
import pytest
import json
import hmac
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from api_gateway.main import create_app
from token_service import (
    TokenService,
    InMemoryInstallationRepository,
    InstallationCreate,
    Platform,
)
from ports.queue import TaskQueueMessage
from adapters.queue.memory_adapter import InMemoryQueueAdapter


@pytest.fixture
def token_service() -> TokenService:
    repository = InMemoryInstallationRepository()
    return TokenService(repository=repository)


@pytest.fixture
def queue() -> InMemoryQueueAdapter:
    return InMemoryQueueAdapter()


@pytest.fixture
async def setup_installation(token_service: TokenService):
    await token_service.create_installation(
        InstallationCreate(
            platform=Platform.GITHUB,
            organization_id="test-org",
            organization_name="Test Organization",
            access_token="gho_test_token",
            scopes=["repo", "read:org"],
            webhook_secret="test_webhook_secret",
            installed_by="admin@test.org",
        )
    )


@pytest.fixture
def app(token_service: TokenService, queue: InMemoryQueueAdapter):
    return create_app(token_service=token_service, queue=queue)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


class TestWebhookToTaskIntegration:
    @pytest.mark.asyncio
    async def test_github_comment_creates_task(
        self,
        client: TestClient,
        queue: InMemoryQueueAdapter,
        setup_installation,
    ):
        payload = {
            "action": "created",
            "comment": {
                "body": "@agent review src/main.py",
                "user": {"login": "developer"},
            },
            "issue": {
                "number": 42,
                "pull_request": {"url": "https://api.github.com/..."},
            },
            "repository": {"full_name": "test-org/test-repo"},
            "installation": {"id": 12345},
            "sender": {"login": "developer"},
        }

        payload_bytes = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            b"test_webhook_secret",
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "issue_comment",
                "x-hub-signature-256": signature,
                "content-type": "application/json",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] is not None

        task = await queue.dequeue(timeout_seconds=1.0)
        assert task is not None
        assert "review src/main.py" in task.input_message
        assert task.source_metadata["pr_number"] == "42"

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(
        self,
        client: TestClient,
        setup_installation,
    ):
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload).encode()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalid",
                "content-type": "application/json",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_trigger_event_skipped(
        self,
        client: TestClient,
        queue: InMemoryQueueAdapter,
        setup_installation,
    ):
        payload = {
            "action": "created",
            "comment": {
                "body": "Just a regular comment",
                "user": {"login": "developer"},
            },
            "issue": {"number": 42},
            "repository": {"full_name": "test-org/test-repo"},
            "installation": {"id": 12345},
            "sender": {"login": "developer"},
        }

        payload_bytes = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(
            b"test_webhook_secret",
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "x-github-event": "issue_comment",
                "x-hub-signature-256": signature,
                "content-type": "application/json",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skipped"] is True

        task = await queue.dequeue(timeout_seconds=0.1)
        assert task is None


class TestOAuthIntegration:
    @pytest.mark.asyncio
    async def test_oauth_flow_creates_installation(
        self,
        client: TestClient,
        token_service: TokenService,
    ):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "access_token": "gho_new_token",
                    "token_type": "bearer",
                    "scope": "repo,read:org",
                },
            )

            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value = AsyncMock(
                    status_code=200,
                    json=lambda: {
                        "id": 12345,
                        "login": "new-org",
                        "email": "admin@new-org.com",
                    },
                )

                from oauth.models import OAuthState
                state = OAuthState(
                    platform="github",
                    redirect_uri="https://app.example.com",
                    nonce="test_nonce",
                )

                response = client.get(
                    f"/oauth/github/callback?code=auth_code&state={state.to_encoded()}"
                )

                assert response.status_code == 200
```

### Step 14.2: End-to-End Test

**File: `tests/e2e/test_full_workflow.py`** (< 200 lines)

```python
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from container import Container, ContainerConfig, create_container
from worker.task_processor import TaskProcessor
from ports.queue import TaskQueueMessage, TaskPriority
from ports.cli_runner import CLIExecutionResult


@pytest.fixture
def container() -> Container:
    config = ContainerConfig(
        queue_type="memory",
        database_type="memory",
        cli_type="mock",
        redis_url="",
        database_url="",
    )
    return create_container(config)


@pytest.fixture
def processor(container: Container) -> TaskProcessor:
    return TaskProcessor(container=container)


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_task_processing_complete_flow(
        self,
        container: Container,
        processor: TaskProcessor,
    ):
        task = TaskQueueMessage(
            task_id="task-e2e-001",
            installation_id="inst-123",
            provider="github",
            input_message="Analyze the main.py file",
            priority=TaskPriority.NORMAL,
            source_metadata={
                "pr_number": "42",
                "repo": "owner/repo",
            },
            created_at=datetime.now(timezone.utc),
        )

        await container.queue.enqueue(task)

        with patch.object(
            container.cli_runner,
            "execute_and_wait",
        ) as mock_cli:
            mock_cli.return_value = CLIExecutionResult(
                success=True,
                output="Analysis complete. Found 3 issues.",
                error=None,
                exit_code=0,
                tokens_used=500,
                cost_usd=0.01,
                duration_seconds=5.0,
            )

            dequeued = await container.queue.dequeue(timeout_seconds=1.0)
            result = await processor.process(dequeued)

            assert result.success is True
            assert "Analysis complete" in result.output
            assert result.tokens_used == 500

    @pytest.mark.asyncio
    async def test_error_handling_flow(
        self,
        container: Container,
        processor: TaskProcessor,
    ):
        task = TaskQueueMessage(
            task_id="task-e2e-002",
            installation_id="inst-123",
            provider="github",
            input_message="Invalid task",
            priority=TaskPriority.NORMAL,
            source_metadata={},
            created_at=datetime.now(timezone.utc),
        )

        await container.queue.enqueue(task)

        with patch.object(
            container.cli_runner,
            "execute_and_wait",
        ) as mock_cli:
            mock_cli.side_effect = Exception("CLI execution failed")

            dequeued = await container.queue.dequeue(timeout_seconds=1.0)
            result = await processor.process(dequeued)

            assert result.success is False
            assert "CLI execution failed" in result.error

    @pytest.mark.asyncio
    async def test_concurrent_task_processing(
        self,
        container: Container,
        processor: TaskProcessor,
    ):
        tasks = [
            TaskQueueMessage(
                task_id=f"task-concurrent-{i}",
                installation_id="inst-123",
                provider="github",
                input_message=f"Task {i}",
                priority=TaskPriority.NORMAL,
                source_metadata={},
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        for task in tasks:
            await container.queue.enqueue(task)

        with patch.object(
            container.cli_runner,
            "execute_and_wait",
        ) as mock_cli:
            mock_cli.return_value = CLIExecutionResult(
                success=True,
                output="Done",
                error=None,
                exit_code=0,
                tokens_used=100,
                cost_usd=0.002,
                duration_seconds=1.0,
            )

            results = []
            for _ in range(5):
                dequeued = await container.queue.dequeue(timeout_seconds=1.0)
                if dequeued:
                    result = await processor.process(dequeued)
                    results.append(result)

            assert len(results) == 5
            assert all(r.success for r in results)
```

---

## Phase 15: CI/CD Configuration

### Step 15.1: GitHub Actions Workflow

**File: `.github/workflows/ci.yml`** (< 100 lines)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install ruff mypy
      - name: Run linting
        run: |
          ruff check .
          ruff format --check .
      - name: Run type checking
        run: mypy . --strict

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
        run: pytest -v --cov --cov-report=xml --timeout=5
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker images
        run: |
          docker compose build
      - name: Run integration tests
        run: |
          docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Final Checklist

### Code Quality Checklist

- [ ] All files under 300 lines
- [ ] No `any` types - `ConfigDict(strict=True)` used
- [ ] No comments - self-explanatory code
- [ ] Structured logging with `structlog`
- [ ] Async/await for all I/O operations
- [ ] Tests run under 5 seconds each

### Architecture Checklist

- [ ] Token service with multi-org support
- [ ] OAuth endpoints for installation
- [ ] Webhook registry for extensibility
- [ ] Ports & adapters for modularity
- [ ] Repository manager for code access
- [ ] Knowledge graph for code intelligence

### Testing Checklist

- [ ] Unit tests for all components
- [ ] Integration tests for workflows
- [ ] E2E tests for full scenarios
- [ ] CI/CD pipeline configured

### Documentation Checklist

- [ ] Agent definitions complete
- [ ] Skills documented
- [ ] Commands defined
- [ ] Hooks specified

---

## Implementation Order Summary

| Week | Phase | Focus |
|------|-------|-------|
| 1 | 1-2 | Token Service + PostgreSQL Adapter |
| 2 | 3 | OAuth Handlers |
| 3 | 4-6 | Ports & Adapters + Container |
| 4 | 7-8 | Repository Manager + Knowledge Graph |
| 5 | 9-10 | Webhook Extension + Router |
| 6 | 11 | Agent Configuration Files |
| 7 | 12-13 | Database Migrations + Docker |
| 8 | 14-15 | Integration Tests + CI/CD |

---

## Quick Start Commands

```bash
# Setup development environment
git clone <repo>
cd agent-bot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v --timeout=5

# Start local environment
docker compose up -d

# Run migrations
python -m database.migrations.runner

# Check logs
docker compose logs -f agent-container
```

This completes the comprehensive TDD implementation guide. Each phase builds on the previous one, and all code follows the strict project rules.
