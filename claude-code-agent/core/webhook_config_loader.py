"""
Webhook Configuration Loader.

Loads webhook configurations from YAML files in the api/webhooks/{name}/config.yaml structure.
Each webhook has its own folder with a config.yaml file that defines:
- Endpoint and metadata
- Agent trigger (prefix, aliases, assignee trigger for Jira)
- Commands with aliases, descriptions, and prompt templates
- Security settings
"""

from pathlib import Path
from typing import List, Dict, Optional
import structlog

from shared.machine_models import WebhookConfig, WebhookYamlConfig

logger = structlog.get_logger()

# Base path for webhook configs
WEBHOOKS_BASE_PATH = Path(__file__).parent.parent / "api" / "webhooks"

# Built-in webhook names (folders with config.yaml)
BUILTIN_WEBHOOKS = ["github", "jira", "slack"]


def load_webhook_config(webhook_name: str) -> Optional[WebhookConfig]:
    """
    Load a single webhook configuration from its config.yaml file.

    Args:
        webhook_name: Name of the webhook (e.g., 'github', 'jira')

    Returns:
        WebhookConfig if found and valid, None otherwise
    """
    config_path = WEBHOOKS_BASE_PATH / webhook_name / "config.yaml"

    if not config_path.exists():
        logger.warning("webhook_config_not_found", webhook=webhook_name, path=str(config_path))
        return None

    try:
        yaml_config = WebhookYamlConfig.from_yaml_file(config_path)
        webhook_config = yaml_config.to_webhook_config()

        logger.info(
            "webhook_config_loaded",
            webhook=webhook_name,
            commands=len(webhook_config.commands),
            endpoint=webhook_config.endpoint,
        )

        return webhook_config

    except Exception as e:
        logger.error(
            "webhook_config_load_error",
            webhook=webhook_name,
            error=str(e),
            path=str(config_path),
        )
        return None


def load_all_webhook_configs() -> List[WebhookConfig]:
    """
    Load all webhook configurations from their config.yaml files.

    Scans the api/webhooks/ directory for subdirectories with config.yaml files.

    Returns:
        List of WebhookConfig objects
    """
    configs: List[WebhookConfig] = []

    # First, load built-in webhooks in order
    for webhook_name in BUILTIN_WEBHOOKS:
        config = load_webhook_config(webhook_name)
        if config:
            configs.append(config)

    # Then, scan for any additional custom webhooks
    if WEBHOOKS_BASE_PATH.exists():
        for item in WEBHOOKS_BASE_PATH.iterdir():
            if item.is_dir() and item.name not in BUILTIN_WEBHOOKS:
                config_file = item / "config.yaml"
                if config_file.exists():
                    config = load_webhook_config(item.name)
                    if config:
                        configs.append(config)

    logger.info("all_webhook_configs_loaded", count=len(configs))
    return configs


def get_webhook_configs_map() -> Dict[str, WebhookConfig]:
    """
    Load all webhook configs and return as a name -> config map.

    Returns:
        Dictionary mapping webhook names to their configs
    """
    configs = load_all_webhook_configs()
    return {config.name: config for config in configs}


def get_webhook_by_name(name: str) -> Optional[WebhookConfig]:
    """
    Get a specific webhook config by name.

    Args:
        name: Webhook name (e.g., 'github', 'jira')

    Returns:
        WebhookConfig if found, None otherwise
    """
    return load_webhook_config(name)


def get_webhook_by_endpoint(endpoint: str) -> Optional[WebhookConfig]:
    """
    Get a specific webhook config by endpoint.

    Args:
        endpoint: Webhook endpoint (e.g., '/webhooks/github')

    Returns:
        WebhookConfig if found, None otherwise
    """
    configs = load_all_webhook_configs()
    for config in configs:
        if config.endpoint == endpoint:
            return config
    return None


def validate_all_configs() -> bool:
    """
    Validate all webhook configurations.

    Checks for:
    - Duplicate endpoints
    - Duplicate names
    - Valid endpoint patterns
    - Required command fields

    Returns:
        True if all configs are valid, False otherwise
    """
    import re

    configs = load_all_webhook_configs()

    if not configs:
        logger.warning("no_webhook_configs_found")
        return False

    # Check for duplicate endpoints
    endpoints = [config.endpoint for config in configs]
    if len(endpoints) != len(set(endpoints)):
        duplicates = [ep for ep in endpoints if endpoints.count(ep) > 1]
        logger.error("duplicate_endpoints", duplicates=duplicates)
        return False

    # Check for duplicate names
    names = [config.name for config in configs]
    if len(names) != len(set(names)):
        duplicates = [n for n in names if names.count(n) > 1]
        logger.error("duplicate_names", duplicates=duplicates)
        return False

    # Validate each config
    for config in configs:
        # Validate endpoint pattern
        if not re.match(r"^/webhooks/[a-z0-9-]+$", config.endpoint):
            logger.error("invalid_endpoint_pattern", webhook=config.name, endpoint=config.endpoint)
            return False

        # Validate commands
        for cmd in config.commands:
            if not cmd.name:
                logger.error("empty_command_name", webhook=config.name)
                return False
            if not cmd.target_agent:
                logger.error("missing_target_agent", webhook=config.name, command=cmd.name)
                return False
            if not cmd.prompt_template:
                logger.error("missing_prompt_template", webhook=config.name, command=cmd.name)
                return False

    logger.info("webhook_configs_validated", count=len(configs))
    return True


def reload_webhook_config(webhook_name: str) -> Optional[WebhookConfig]:
    """
    Reload a specific webhook configuration (useful for hot-reloading).

    Args:
        webhook_name: Name of the webhook to reload

    Returns:
        Updated WebhookConfig if successful, None otherwise
    """
    logger.info("reloading_webhook_config", webhook=webhook_name)
    return load_webhook_config(webhook_name)


def get_agent_trigger_info(webhook_name: str) -> Optional[Dict]:
    """
    Get agent trigger information for a webhook.

    Returns the prefix, aliases, and assignee_trigger (for Jira) configuration.

    Args:
        webhook_name: Name of the webhook

    Returns:
        Dictionary with trigger info, or None if not found
    """
    config_path = WEBHOOKS_BASE_PATH / webhook_name / "config.yaml"

    if not config_path.exists():
        return None

    try:
        yaml_config = WebhookYamlConfig.from_yaml_file(config_path)
        return {
            "prefix": yaml_config.agent_trigger.prefix,
            "aliases": yaml_config.agent_trigger.aliases,
            "assignee_trigger": yaml_config.agent_trigger.assignee_trigger,
        }
    except Exception as e:
        logger.error("get_trigger_info_error", webhook=webhook_name, error=str(e))
        return None


# Legacy class for backward compatibility
class WebhookConfigLoader:
    """Legacy class for backward compatibility."""

    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or WEBHOOKS_BASE_PATH

    def load_webhook_config(self, webhook_name: str) -> WebhookConfig:
        config = load_webhook_config(webhook_name)
        if not config:
            raise FileNotFoundError(f"Webhook config not found: {webhook_name}")
        return config

    def load_all_webhook_configs(self) -> Dict[str, WebhookConfig]:
        return get_webhook_configs_map()


webhook_config_loader = WebhookConfigLoader()
