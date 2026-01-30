import structlog

from .protocol import WebhookHandlerProtocol

logger = structlog.get_logger()


class WebhookRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, WebhookHandlerProtocol] = {}

    def register(
        self, provider: str, handler: WebhookHandlerProtocol
    ) -> None:
        logger.info("registering_webhook_handler", provider=provider)
        self._handlers[provider] = handler

    def unregister(self, provider: str) -> None:
        if provider in self._handlers:
            logger.info("unregistering_webhook_handler", provider=provider)
            del self._handlers[provider]

    def get_handler(self, provider: str) -> WebhookHandlerProtocol | None:
        return self._handlers.get(provider)

    def list_providers(self) -> list[str]:
        return list(self._handlers.keys())

    def has_handler(self, provider: str) -> bool:
        return provider in self._handlers
