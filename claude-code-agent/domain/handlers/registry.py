"""
Typed handler registry for task completion handlers.

This module replaces string-based handler registration with type-safe
handlers using Python protocols. This provides:
- Compile-time validation of handler signatures
- IDE autocompletion and documentation
- No runtime import errors from invalid paths
"""

from typing import Awaitable, Callable, Dict, List, Optional, TypeVar

from domain.models.task_completion import TaskCompletionContext, TaskCompletionResult
from domain.models.webhook_payload import WebhookSource


# Type alias for task completion handlers
TaskCompletionHandler = Callable[[TaskCompletionContext], Awaitable[TaskCompletionResult]]

T = TypeVar("T")


class HandlerRegistry:
    """
    Registry for task completion handlers.

    Provides type-safe registration and lookup of handlers by webhook source.
    Handlers must accept a TaskCompletionContext and return TaskCompletionResult.

    Example:
        registry = HandlerRegistry()

        @registry.handler(WebhookSource.GITHUB)
        async def handle_github(ctx: TaskCompletionContext) -> TaskCompletionResult:
            # Handle GitHub task completion
            return TaskCompletionResult(comment_posted=True)

        # Later, invoke the handler
        handler = registry.get(WebhookSource.GITHUB)
        result = await handler(context)
    """

    def __init__(self):
        self._handlers: Dict[WebhookSource, TaskCompletionHandler] = {}

    def register(
        self,
        source: WebhookSource,
        handler: TaskCompletionHandler,
        *,
        overwrite: bool = False,
    ) -> None:
        """
        Register a handler for a webhook source.

        Args:
            source: The webhook source (GITHUB, JIRA, SLACK)
            handler: The async handler function
            overwrite: If True, allow overwriting existing handlers

        Raises:
            ValueError: If handler already registered and overwrite is False
        """
        if source in self._handlers and not overwrite:
            raise ValueError(
                f"Handler already registered for {source.value}. "
                "Use overwrite=True to replace."
            )
        self._handlers[source] = handler

    def handler(
        self,
        source: WebhookSource,
        *,
        overwrite: bool = False,
    ):
        """
        Decorator for registering a handler.

        Example:
            @registry.handler(WebhookSource.GITHUB)
            async def handle_github(ctx: TaskCompletionContext) -> TaskCompletionResult:
                ...
        """

        def decorator(func: TaskCompletionHandler) -> TaskCompletionHandler:
            self.register(source, func, overwrite=overwrite)
            return func

        return decorator

    def get(self, source: WebhookSource) -> TaskCompletionHandler:
        """
        Get the handler for a webhook source.

        Args:
            source: The webhook source

        Returns:
            The registered handler

        Raises:
            KeyError: If no handler is registered for the source
        """
        if source not in self._handlers:
            raise KeyError(f"No handler registered for {source.value}")
        return self._handlers[source]

    def get_or_default(
        self,
        source: WebhookSource,
        default: TaskCompletionHandler,
    ) -> TaskCompletionHandler:
        """
        Get the handler for a source, or return a default.

        Args:
            source: The webhook source
            default: Default handler to return if not registered

        Returns:
            The registered handler or the default
        """
        return self._handlers.get(source, default)

    def has_handler(self, source: WebhookSource) -> bool:
        """Check if a handler is registered for a source."""
        return source in self._handlers

    def list_sources(self) -> List[WebhookSource]:
        """List all sources with registered handlers."""
        return list(self._handlers.keys())

    def unregister(self, source: WebhookSource) -> Optional[TaskCompletionHandler]:
        """
        Unregister a handler.

        Args:
            source: The webhook source to unregister

        Returns:
            The unregistered handler, or None if not found
        """
        return self._handlers.pop(source, None)

    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()


# Global handler registry instance
# Import and register handlers at application startup
completion_handlers = HandlerRegistry()
