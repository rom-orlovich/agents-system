from typing import Awaitable, Callable, Dict, List, Optional, TypeVar

from domain.models.task_completion import TaskCompletionContext, TaskCompletionResult
from domain.models.webhook_payload import WebhookSource


TaskCompletionHandler = Callable[[TaskCompletionContext], Awaitable[TaskCompletionResult]]

T = TypeVar("T")


class HandlerRegistry:

    def __init__(self):
        self._handlers: Dict[WebhookSource, TaskCompletionHandler] = {}

    def register(
        self,
        source: WebhookSource,
        handler: TaskCompletionHandler,
        *,
        overwrite: bool = False,
    ) -> None:
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
        def decorator(func: TaskCompletionHandler) -> TaskCompletionHandler:
            self.register(source, func, overwrite=overwrite)
            return func

        return decorator

    def get(self, source: WebhookSource) -> TaskCompletionHandler:
        if source not in self._handlers:
            raise KeyError(f"No handler registered for {source.value}")
        return self._handlers[source]

    def get_or_default(
        self,
        source: WebhookSource,
        default: TaskCompletionHandler,
    ) -> TaskCompletionHandler:
        return self._handlers.get(source, default)

    def has_handler(self, source: WebhookSource) -> bool:
        return source in self._handlers

    def list_sources(self) -> List[WebhookSource]:
        return list(self._handlers.keys())

    def unregister(self, source: WebhookSource) -> Optional[TaskCompletionHandler]:
        return self._handlers.pop(source, None)

    def clear(self) -> None:
        self._handlers.clear()


completion_handlers = HandlerRegistry()
