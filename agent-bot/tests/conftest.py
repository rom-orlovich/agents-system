"""Shared test fixtures for agent-bot services."""

import asyncio
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client for testing."""
    redis = MagicMock()
    redis.lpush = AsyncMock(return_value=1)
    redis.brpop = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=1)
    redis.hget = AsyncMock(return_value=None)
    redis.publish = AsyncMock(return_value=1)
    redis.aclose = AsyncMock()
    redis.from_url = MagicMock(return_value=redis)
    return redis


@pytest.fixture
def mock_settings() -> MagicMock:
    """Test environment settings."""
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379/15"
    settings.redis_host = "localhost"
    settings.redis_port = 6379
    settings.redis_db = 15
    settings.postgres_url = "postgresql://test:test@localhost/test"
    settings.cli_provider = "claude"
    settings.max_concurrent_tasks = 5
    settings.task_timeout_seconds = 3600
    settings.claude_model_complex = "opus"
    settings.claude_model_execution = "sonnet"
    settings.cursor_model_complex = "claude-sonnet-4.5"
    settings.cursor_model_execution = "composer-1"
    settings.github_webhook_secret = "test-secret"
    settings.jira_webhook_secret = "test-jira-secret"
    settings.slack_signing_secret = "test-slack-secret"
    settings.sentry_webhook_secret = "test-sentry-secret"
    settings.port = 8080
    return settings


@pytest.fixture
def github_webhook_signature():
    """GitHub webhook signature generator."""
    def _sign(payload: bytes, secret: str) -> str:
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    return _sign


@pytest.fixture
def jira_webhook_signature():
    """Jira webhook signature generator."""
    def _sign(payload: bytes, secret: str) -> str:
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    return _sign


@pytest.fixture
def slack_webhook_signature():
    """Slack webhook signature generator."""
    def _sign(payload: bytes, secret: str, timestamp: str) -> str:
        sig_basestring = f"v0:{timestamp}:{payload.decode()}"
        signature = hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v0={signature}"
    return _sign


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Sample task data for testing."""
    return {
        "task_id": "test-task-001",
        "prompt": "Fix the authentication bug",
        "repo_path": "/app/repos/test-repo",
        "agent_type": "executor",
        "source": "github",
        "metadata": {
            "issue_number": 123,
            "repository": "test-org/test-repo",
        },
    }


@pytest.fixture
def sample_session_data() -> dict[str, Any]:
    """Sample session data for testing."""
    return {
        "session_id": "test-session-001",
        "user_id": "test-user",
        "machine_id": "test-machine",
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "total_cost_usd": 0.0,
        "total_tasks": 0,
        "active": True,
    }


@pytest.fixture
def iso_timestamp() -> str:
    """Current ISO timestamp for testing."""
    return datetime.now(timezone.utc).isoformat()
