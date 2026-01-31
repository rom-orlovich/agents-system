"""
Webhook configurations loaded from YAML config files.

Each webhook has its own config.yaml file in: api/webhooks/{name}/config.yaml

This module provides easy access to the loaded configurations and maintains
backward compatibility with code that expects the old hardcoded configs.

Configuration files support:
- Agent trigger settings (prefix, aliases, Jira assignee trigger)
- Multiple commands with aliases and descriptions
- Prompt templates with {{placeholders}}
- Security settings (signature verification)

To modify webhook behavior, edit the config.yaml file in the webhook's folder.
"""

from typing import List, Optional
import structlog

from shared.machine_models import WebhookConfig
from core.webhook_config_loader import (
    load_all_webhook_configs,
    load_webhook_config,
    validate_all_configs,
    get_agent_trigger_info,
)

logger = structlog.get_logger()

# =============================================================================
# LOAD WEBHOOK CONFIGS FROM YAML FILES
# =============================================================================

# Load all configs at module initialization
_loaded_configs: List[WebhookConfig] = load_all_webhook_configs()

# Create individual webhook references for backward compatibility
GITHUB_WEBHOOK: Optional[WebhookConfig] = next(
    (c for c in _loaded_configs if c.name == "github"), None
)
JIRA_WEBHOOK: Optional[WebhookConfig] = next(
    (c for c in _loaded_configs if c.name == "jira"), None
)
SLACK_WEBHOOK: Optional[WebhookConfig] = next(
    (c for c in _loaded_configs if c.name == "slack"), None
)

# Collect all configs
WEBHOOK_CONFIGS: List[WebhookConfig] = _loaded_configs


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def validate_webhook_configs() -> None:
    """Validate all webhook configurations at startup."""
    # Check critical webhooks are loaded
    critical_webhooks = [
        ("github", GITHUB_WEBHOOK),
        ("jira", JIRA_WEBHOOK),
        ("slack", SLACK_WEBHOOK),
    ]
    missing = [name for name, cfg in critical_webhooks if cfg is None]

    if missing:
        raise ValueError(
            f"Critical webhook configurations missing: {', '.join(missing)}. "
            f"Check YAML files in api/webhooks/{{name}}/config.yaml"
        )

    # Validate existing configs
    if not validate_all_configs():
        raise ValueError(
            "Webhook configuration validation failed. Check logs for details."
        )
    logger.info("webhook_configs_validated", count=len(WEBHOOK_CONFIGS))


def get_webhook_by_endpoint(endpoint: str) -> WebhookConfig:
    """Get webhook config by endpoint."""
    for config in WEBHOOK_CONFIGS:
        if config.endpoint == endpoint:
            return config
    raise ValueError(f"Webhook not found for endpoint: {endpoint}")


def get_webhook_by_name(name: str) -> Optional[WebhookConfig]:
    """Get webhook config by name."""
    for config in WEBHOOK_CONFIGS:
        if config.name == name:
            return config
    return None


def reload_webhook(name: str) -> Optional[WebhookConfig]:
    """
    Reload a specific webhook configuration from its YAML file.

    Useful for hot-reloading configuration changes without restarting.

    Args:
        name: Webhook name (e.g., 'github', 'jira')

    Returns:
        Updated WebhookConfig if successful, None otherwise
    """
    global _loaded_configs, WEBHOOK_CONFIGS
    global GITHUB_WEBHOOK, JIRA_WEBHOOK, SLACK_WEBHOOK

    new_config = load_webhook_config(name)
    if not new_config:
        return None

    # Update the loaded configs list
    _loaded_configs = [c for c in _loaded_configs if c.name != name]
    _loaded_configs.append(new_config)
    WEBHOOK_CONFIGS = _loaded_configs

    # Update individual references
    if name == "github":
        GITHUB_WEBHOOK = new_config
    elif name == "jira":
        JIRA_WEBHOOK = new_config
    elif name == "slack":
        SLACK_WEBHOOK = new_config

    logger.info("webhook_reloaded", name=name)
    return new_config


def reload_all_webhooks() -> List[WebhookConfig]:
    """
    Reload all webhook configurations from YAML files.

    Returns:
        List of reloaded WebhookConfig objects
    """
    global _loaded_configs, WEBHOOK_CONFIGS
    global GITHUB_WEBHOOK, JIRA_WEBHOOK, SLACK_WEBHOOK

    _loaded_configs = load_all_webhook_configs()
    WEBHOOK_CONFIGS = _loaded_configs

    # Update individual references
    GITHUB_WEBHOOK = next((c for c in _loaded_configs if c.name == "github"), None)
    JIRA_WEBHOOK = next((c for c in _loaded_configs if c.name == "jira"), None)
    SLACK_WEBHOOK = next((c for c in _loaded_configs if c.name == "slack"), None)

    logger.info("all_webhooks_reloaded", count=len(_loaded_configs))
    return _loaded_configs


def get_trigger_prefixes(webhook_name: str) -> List[str]:
    """
    Get all valid trigger prefixes for a webhook (prefix + aliases).

    Args:
        webhook_name: Name of the webhook

    Returns:
        List of trigger prefixes (e.g., ['@agent', '@claude', '@bot'])
    """
    trigger_info = get_agent_trigger_info(webhook_name)
    if not trigger_info:
        return ["@agent"]  # Default fallback

    prefixes = [trigger_info["prefix"]] if trigger_info["prefix"] else []
    prefixes.extend(trigger_info.get("aliases", []))
    return prefixes


def get_assignee_trigger(webhook_name: str) -> Optional[str]:
    """
    Get the assignee trigger for a webhook (Jira-specific).

    When a ticket is assigned to this user, the agent is triggered.

    Args:
        webhook_name: Name of the webhook

    Returns:
        Assignee name that triggers the agent, or None
    """
    trigger_info = get_agent_trigger_info(webhook_name)
    if not trigger_info:
        return None
    return trigger_info.get("assignee_trigger")
