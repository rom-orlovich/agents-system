"""
Webhook handlers auto-discovery.

This module automatically discovers and registers all webhook handlers
in this directory.
"""

import logging
import importlib
import inspect
from pathlib import Path
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.webhook_registry import WebhookRegistry
    from core.webhook_base import BaseWebhookHandler

logger = logging.getLogger(__name__)


def discover_webhook_modules() -> List[str]:
    """
    Discover all webhook handler modules in this directory.

    Returns:
        List of module names (without .py extension)
    """
    webhooks_dir = Path(__file__).parent
    webhook_files = webhooks_dir.glob("*_webhook.py")

    modules = []
    for file in webhook_files:
        module_name = file.stem  # Remove .py extension
        modules.append(module_name)

    logger.debug(f"Discovered webhook modules: {modules}")
    return modules


def auto_register_webhooks(registry: "WebhookRegistry") -> None:
    """
    Auto-discover and register all webhook handlers.

    Args:
        registry: WebhookRegistry instance to register handlers with
    """
    from core.webhook_base import BaseWebhookHandler

    webhook_modules = discover_webhook_modules()

    for module_name in webhook_modules:
        try:
            # Import module
            module = importlib.import_module(f"webhooks.{module_name}")

            # Find all BaseWebhookHandler subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip the base class itself
                if obj is BaseWebhookHandler:
                    continue

                # Check if it's a subclass of BaseWebhookHandler
                if issubclass(obj, BaseWebhookHandler):
                    # Instantiate and register
                    handler = obj()
                    registry.register(handler)

        except Exception as e:
            logger.error(f"Failed to load webhook module '{module_name}': {e}")
            logger.exception(e)


__all__ = [
    "auto_register_webhooks",
    "discover_webhook_modules",
]
