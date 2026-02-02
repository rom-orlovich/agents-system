"""Agent engine test fixtures."""

from unittest.mock import MagicMock

import pytest

from .factories import TaskFactory, SessionFactory


@pytest.fixture
def task_factory():
    """Task factory fixture."""
    return TaskFactory()


@pytest.fixture
def session_factory():
    """Session factory fixture."""
    return SessionFactory()


@pytest.fixture
def mock_engine_settings():
    """Mock settings for agent engine."""
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379/0"
    settings.cli_provider = "claude"
    settings.max_concurrent_tasks = 5
    settings.task_timeout_seconds = 3600
    settings.claude_model_complex = "opus"
    settings.claude_model_execution = "sonnet"
    settings.cursor_model_complex = "claude-sonnet-4.5"
    settings.cursor_model_execution = "composer-1"
    settings.port = 8080
    return settings
