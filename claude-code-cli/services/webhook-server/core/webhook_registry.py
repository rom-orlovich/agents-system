"""
Central registry for webhook handlers.
"""

import logging
from typing import Dict, List, Optional

from .webhook_base import BaseWebhookHandler, WebhookMetadata

logger = logging.getLogger(__name__)


class WebhookRegistry:
    """
    Central registry for all webhook handlers.

    Provides:
    - Registration of webhook handlers
    - Auto-discovery of handlers in webhooks/ directory
    - Handler lookup by name
    - Metadata listing
    """

    def __init__(self):
        self._handlers: Dict[str, BaseWebhookHandler] = {}
        self._enabled_count = 0
        self._disabled_count = 0

    def register(self, handler: BaseWebhookHandler) -> None:
        """
        Register a webhook handler.

        Args:
            handler: Instance of BaseWebhookHandler subclass
        """
        metadata = handler.metadata

        if not metadata.enabled:
            logger.info(
                f"Webhook '{metadata.name}' is disabled (set enabled=True to enable)"
            )
            self._disabled_count += 1
            return

        if metadata.name in self._handlers:
            logger.warning(
                f"Webhook '{metadata.name}' already registered, overwriting"
            )

        self._handlers[metadata.name] = handler
        self._enabled_count += 1

        logger.info(
            f"✓ Registered webhook: {metadata.name} at {metadata.endpoint}"
        )

    def get_handler(self, name: str) -> Optional[BaseWebhookHandler]:
        """
        Get handler by name.

        Args:
            name: Webhook name (e.g., 'jira')

        Returns:
            Handler instance, or None if not found
        """
        return self._handlers.get(name)

    def list_handlers(self) -> List[WebhookMetadata]:
        """
        List all registered webhook metadata.

        Returns:
            List of WebhookMetadata for all registered handlers
        """
        return [handler.metadata for handler in self._handlers.values()]

    def get_handler_names(self) -> List[str]:
        """
        Get list of all registered webhook names.

        Returns:
            List of webhook names
        """
        return list(self._handlers.keys())

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dict with enabled, disabled, and total counts
        """
        return {
            "enabled": self._enabled_count,
            "disabled": self._disabled_count,
            "total": self._enabled_count + self._disabled_count,
        }

    def auto_discover(self) -> None:
        """
        Auto-discover all webhook handlers in webhooks/ directory.

        Imports the webhooks module which should call discover_webhooks()
        and register all found handlers.
        """
        try:
            # Import webhooks module which will auto-discover handlers
            from webhooks import auto_register_webhooks

            auto_register_webhooks(self)

            stats = self.get_stats()
            logger.info(
                f"Auto-discovery complete: {stats['enabled']} enabled, "
                f"{stats['disabled']} disabled, {stats['total']} total"
            )

        except ImportError as e:
            logger.error(f"Failed to import webhooks module: {e}")
            logger.error("Make sure webhooks/__init__.py exists and is valid")

    def clear(self) -> None:
        """Clear all registered handlers (mainly for testing)."""
        self._handlers.clear()
        self._enabled_count = 0
        self._disabled_count = 0


# Global registry instance
webhook_registry = WebhookRegistry()
