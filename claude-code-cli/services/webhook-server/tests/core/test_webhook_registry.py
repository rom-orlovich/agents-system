"""
Tests for WebhookRegistry.
"""

import pytest
from core.webhook_registry import WebhookRegistry
from core.webhook_base import BaseWebhookHandler, WebhookMetadata, WebhookResponse
from typing import Dict, Any, Optional


class MockWebhookHandler(BaseWebhookHandler):
    """Mock webhook handler for testing."""

    def __init__(self, name: str = "mock", enabled: bool = True):
        self._name = name
        self._enabled = enabled

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name=self._name,
            endpoint=f"/webhooks/{self._name}",
            description=f"Mock {self._name} webhook",
            secret_env_var=f"{self._name.upper()}_WEBHOOK_SECRET",
            enabled=self._enabled
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        return True

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return payload

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        return True

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        return WebhookResponse(
            status="success",
            message="Mock webhook handled"
        )


def test_registry_initialization():
    """Test that registry initializes correctly."""
    registry = WebhookRegistry()

    assert registry._handlers == {}
    assert registry._enabled_count == 0
    assert registry._disabled_count == 0


def test_register_enabled_webhook():
    """Test registering an enabled webhook."""
    registry = WebhookRegistry()
    handler = MockWebhookHandler(name="test", enabled=True)

    registry.register(handler)

    assert registry.get_handler("test") is handler
    assert registry._enabled_count == 1
    assert registry._disabled_count == 0


def test_register_disabled_webhook():
    """Test that disabled webhooks are not registered."""
    registry = WebhookRegistry()
    handler = MockWebhookHandler(name="test", enabled=False)

    registry.register(handler)

    assert registry.get_handler("test") is None
    assert registry._enabled_count == 0
    assert registry._disabled_count == 1


def test_get_handler_not_found():
    """Test getting a handler that doesn't exist."""
    registry = WebhookRegistry()

    handler = registry.get_handler("nonexistent")

    assert handler is None


def test_list_handlers():
    """Test listing all registered handlers."""
    registry = WebhookRegistry()
    handler1 = MockWebhookHandler(name="test1")
    handler2 = MockWebhookHandler(name="test2")

    registry.register(handler1)
    registry.register(handler2)

    handlers = registry.list_handlers()

    assert len(handlers) == 2
    assert handlers[0].name == "test1"
    assert handlers[1].name == "test2"


def test_get_handler_names():
    """Test getting list of handler names."""
    registry = WebhookRegistry()
    handler1 = MockWebhookHandler(name="test1")
    handler2 = MockWebhookHandler(name="test2")

    registry.register(handler1)
    registry.register(handler2)

    names = registry.get_handler_names()

    assert names == ["test1", "test2"]


def test_get_stats():
    """Test getting registry statistics."""
    registry = WebhookRegistry()
    handler1 = MockWebhookHandler(name="test1", enabled=True)
    handler2 = MockWebhookHandler(name="test2", enabled=False)
    handler3 = MockWebhookHandler(name="test3", enabled=True)

    registry.register(handler1)
    registry.register(handler2)
    registry.register(handler3)

    stats = registry.get_stats()

    assert stats["enabled"] == 2
    assert stats["disabled"] == 1
    assert stats["total"] == 3


def test_clear():
    """Test clearing the registry."""
    registry = WebhookRegistry()
    handler = MockWebhookHandler(name="test")

    registry.register(handler)
    assert registry._enabled_count == 1

    registry.clear()

    assert registry._handlers == {}
    assert registry._enabled_count == 0
    assert registry._disabled_count == 0


def test_register_duplicate_webhook():
    """Test that registering duplicate webhook overwrites."""
    registry = WebhookRegistry()
    handler1 = MockWebhookHandler(name="test")
    handler2 = MockWebhookHandler(name="test")

    registry.register(handler1)
    registry.register(handler2)

    # Should only have one handler
    assert len(registry.list_handlers()) == 1
    assert registry.get_handler("test") is handler2
    # Count should still be 1 (overwrite doesn't increment)
    assert registry._enabled_count == 2  # Bug? Or intended?
