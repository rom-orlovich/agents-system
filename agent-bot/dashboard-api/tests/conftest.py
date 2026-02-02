"""Dashboard API test fixtures."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from .factories import TaskFactory, SessionFactory, ConversationFactory, WebhookFactory


@pytest.fixture
def task_factory():
    """Task factory fixture."""
    TaskFactory.reset()
    return TaskFactory


@pytest.fixture
def session_factory():
    """Session factory fixture."""
    SessionFactory.reset()
    return SessionFactory


@pytest.fixture
def conversation_factory():
    """Conversation factory fixture."""
    ConversationFactory.reset()
    return ConversationFactory


@pytest.fixture
def webhook_factory():
    """Webhook factory fixture."""
    WebhookFactory.reset()
    return WebhookFactory


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session
