"""Pytest configuration and fixtures for webhook-server tests."""

import os
import sys
import pytest
from unittest.mock import MagicMock


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables and mocks before tests run."""
    # Set required environment variables for tests
    os.environ.setdefault("GITHUB_TOKEN", "test_token_123")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    # Mock the agents module before any imports happen
    # This prevents ModuleNotFoundError when dashboard_api tries to import agent_registry
    mock_agent_registry = MagicMock()
    mock_agent_registry.list_agents = MagicMock(return_value=[])
    mock_agent_registry.get_stats = MagicMock(return_value={})
    mock_agent_registry.get_execution_history = MagicMock(return_value=[])

    mock_agents_core = MagicMock()
    mock_agents_core.agent_registry = mock_agent_registry

    mock_agents = MagicMock()
    mock_agents.core = mock_agents_core

    sys.modules['agents'] = mock_agents
    sys.modules['agents.core'] = mock_agents_core
    sys.modules['agents.core.agent_registry'] = mock_agent_registry

    yield

    # Cleanup if needed
