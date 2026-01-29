"""Webhook utility functions for safe config access."""
from typing import Optional, List
import structlog
from shared.machine_models import WebhookConfig, WebhookCommand

logger = structlog.get_logger()


def get_webhook_commands(
    webhook_config: Optional[WebhookConfig],
    webhook_name: str
) -> List[WebhookCommand]:
    """
    Safely get commands from webhook config. Returns empty list if None.

    Args:
        webhook_config: Webhook configuration object (can be None)
        webhook_name: Name of webhook for logging

    Returns:
        List of webhook commands, or empty list if config is None
    """
    if webhook_config is None:
        logger.error(
            "webhook_config_not_loaded",
            webhook_name=webhook_name,
            message=f"{webhook_name} webhook configuration not loaded"
        )
        return []
    return webhook_config.commands
