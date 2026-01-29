from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog
from shared.machine_models import WebhookCommand

logger = structlog.get_logger()


def load_webhook_config_from_yaml(config_file_path: Path):
    """Load webhook config from YAML file using Pydantic models."""
    from shared.machine_models import WebhookYamlConfig

    if not config_file_path.exists():
        logger.error("webhook_config_not_found", path=str(config_file_path))
        return None

    try:
        yaml_config = WebhookYamlConfig.from_yaml_file(config_file_path)
        webhook_config = yaml_config.to_webhook_config()
        logger.info("webhook_config_loaded",
                   webhook=webhook_config.name,
                   commands=len(webhook_config.commands))
        return webhook_config
    except Exception as e:
        logger.error("webhook_config_load_error",
                    path=str(config_file_path),
                    error=str(e))
        return None


def check_trigger_prefix(text: str, prefix: str, aliases: List[str]) -> bool:
    """Check if text starts with trigger prefix or any alias."""
    if not text:
        return False

    text_lower = text.lower().strip()
    all_triggers = [prefix.lower()] + [alias.lower() for alias in aliases]

    return any(text_lower.startswith(trigger) for trigger in all_triggers)


def match_command_from_text(
    text: str,
    commands: List[Dict[str, Any]],
    prefix: str,
    aliases: List[str]
) -> Optional[Dict[str, Any]]:
    """Match a command from text based on prefix and command names/aliases."""
    if not text or not check_trigger_prefix(text, prefix, aliases):
        return None

    text_lower = text.lower().strip()

    for trigger in [prefix] + aliases:
        if text_lower.startswith(trigger.lower()):
            command_text = text_lower[len(trigger):].strip()

            for cmd in commands:
                cmd_name = cmd["name"].lower()
                if command_text.startswith(cmd_name):
                    return cmd

                if "aliases" in cmd:
                    for alias in cmd["aliases"]:
                        if command_text.startswith(alias.lower()):
                            return cmd

    return None


def get_template_content(command: WebhookCommand, webhook_name: str) -> Optional[str]:
    """
    Get template content for a command.

    If command has template_file, loads from file.
    Otherwise, uses inline prompt_template.

    Args:
        command: WebhookCommand with either template_file or prompt_template
        webhook_name: Name of webhook (github, jira, slack) for locating template files

    Returns:
        Template content string or None if not found
    """
    from api.webhooks.common.template_loader import get_template_loader

    if command.template_file:
        loader = get_template_loader(webhook_name)
        template_content = loader.load_template(command.template_file)

        if template_content:
            logger.debug(
                "template_loaded_from_file",
                webhook=webhook_name,
                command=command.name,
                template_file=command.template_file
            )
            return template_content
        else:
            logger.error(
                "template_file_not_found",
                webhook=webhook_name,
                command=command.name,
                template_file=command.template_file
            )
            return None

    elif command.prompt_template:
        logger.debug(
            "using_inline_prompt_template",
            webhook=webhook_name,
            command=command.name
        )
        return command.prompt_template

    else:
        logger.error(
            "no_template_source",
            webhook=webhook_name,
            command=command.name
        )
        return None
