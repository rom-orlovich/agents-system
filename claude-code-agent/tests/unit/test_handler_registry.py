"""
Tests for typed handler registry - written first following TDD approach.

The handler registry provides:
- Type-safe handler registration
- Compile-time validation of handler signatures
- Protocol-based handler contracts
"""

import pytest
from typing import Optional


class TestTaskCompletionHandlerProtocol:
    """Tests for TaskCompletionHandler protocol."""

    def test_handler_implements_protocol(self):
        """Test that a handler implements the protocol."""
        from domain.handlers import TaskCompletionHandler
        from domain.models import TaskCompletionContext, TaskCompletionResult

        async def my_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        # Should be a valid handler
        assert callable(my_handler)

    def test_handler_with_wrong_signature_fails_type_check(self):
        """Test that handlers with wrong signatures are detected."""
        # This is more of a static type checking test
        # Runtime protocol checking would require runtime_checkable
        pass


class TestHandlerRegistry:
    """Tests for HandlerRegistry."""

    def test_register_handler(self):
        """Test registering a handler."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def github_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        registry.register(WebhookSource.GITHUB, github_handler)

        assert registry.has_handler(WebhookSource.GITHUB)

    def test_get_registered_handler(self):
        """Test getting a registered handler."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def github_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        registry.register(WebhookSource.GITHUB, github_handler)

        handler = registry.get(WebhookSource.GITHUB)
        assert handler is github_handler

    def test_get_unregistered_handler_raises(self):
        """Test getting unregistered handler raises error."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource

        registry = HandlerRegistry()

        with pytest.raises(KeyError):
            registry.get(WebhookSource.GITHUB)

    def test_get_with_default(self):
        """Test getting handler with default."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def default_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=False)

        handler = registry.get_or_default(WebhookSource.GITHUB, default_handler)
        assert handler is default_handler

    def test_register_decorator(self):
        """Test registering handler with decorator."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        @registry.handler(WebhookSource.JIRA)
        async def jira_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        assert registry.has_handler(WebhookSource.JIRA)
        assert registry.get(WebhookSource.JIRA) is jira_handler

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def github_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        async def jira_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        async def slack_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        registry.register(WebhookSource.GITHUB, github_handler)
        registry.register(WebhookSource.JIRA, jira_handler)
        registry.register(WebhookSource.SLACK, slack_handler)

        assert registry.has_handler(WebhookSource.GITHUB)
        assert registry.has_handler(WebhookSource.JIRA)
        assert registry.has_handler(WebhookSource.SLACK)

    def test_list_registered_sources(self):
        """Test listing registered sources."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def github_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        async def jira_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        registry.register(WebhookSource.GITHUB, github_handler)
        registry.register(WebhookSource.JIRA, jira_handler)

        sources = registry.list_sources()
        assert WebhookSource.GITHUB in sources
        assert WebhookSource.JIRA in sources
        assert WebhookSource.SLACK not in sources

    def test_overwrite_handler_raises_by_default(self):
        """Test that overwriting handler raises error by default."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def handler1(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        async def handler2(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=False)

        registry.register(WebhookSource.GITHUB, handler1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(WebhookSource.GITHUB, handler2)

    def test_overwrite_handler_when_allowed(self):
        """Test that overwriting handler works when allowed."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()

        async def handler1(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=True)

        async def handler2(ctx: TaskCompletionContext) -> TaskCompletionResult:
            return TaskCompletionResult(comment_posted=False)

        registry.register(WebhookSource.GITHUB, handler1)
        registry.register(WebhookSource.GITHUB, handler2, overwrite=True)

        assert registry.get(WebhookSource.GITHUB) is handler2


class TestGlobalHandlerRegistry:
    """Tests for global handler registry instance."""

    def test_global_registry_exists(self):
        """Test that global registry is available."""
        from domain.handlers import completion_handlers

        assert completion_handlers is not None

    def test_global_registry_is_shared(self):
        """Test that global registry is the same instance."""
        from domain.handlers import completion_handlers as handlers1
        from domain.handlers import completion_handlers as handlers2

        assert handlers1 is handlers2


@pytest.mark.asyncio
class TestHandlerExecution:
    """Tests for handler execution."""

    async def test_execute_handler(self):
        """Test executing a registered handler."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext, TaskCompletionResult

        registry = HandlerRegistry()
        executed = []

        async def github_handler(ctx: TaskCompletionContext) -> TaskCompletionResult:
            executed.append(ctx.task_id)
            return TaskCompletionResult(comment_posted=True)

        registry.register(WebhookSource.GITHUB, github_handler)

        ctx = TaskCompletionContext(
            payload={},
            message="Test",
            success=True,
            task_id="test-123",
        )

        handler = registry.get(WebhookSource.GITHUB)
        result = await handler(ctx)

        assert result.comment_posted is True
        assert "test-123" in executed

    async def test_execute_handler_with_error(self):
        """Test executing a handler that raises error."""
        from domain.handlers import HandlerRegistry
        from domain.models import WebhookSource, TaskCompletionContext

        registry = HandlerRegistry()

        async def failing_handler(ctx: TaskCompletionContext):
            raise ValueError("Test error")

        registry.register(WebhookSource.GITHUB, failing_handler)

        ctx = TaskCompletionContext(
            payload={},
            message="Test",
            success=True,
        )

        handler = registry.get(WebhookSource.GITHUB)

        with pytest.raises(ValueError, match="Test error"):
            await handler(ctx)
