from typing import Optional, Tuple

from domain.models.commands import get_commands_config, CommandsConfig


def _get_config() -> CommandsConfig:
    return get_commands_config()


def extract_command(text: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None

    config = _get_config()
    match = config.command_pattern.search(text)
    if not match:
        return None

    command = match.group(2).lower()
    content = (match.group(3) or "").strip()

    return (command, content)


def extract_command_with_prefix(text: str) -> Optional[Tuple[str, str, str]]:
    if not text:
        return None

    config = _get_config()
    match = config.command_pattern.search(text)
    if not match:
        return None

    prefix = match.group(1).lower()
    command = match.group(2).lower()
    content = (match.group(3) or "").strip()

    return (prefix, command, content)


def has_agent_mention(text: str) -> bool:
    if not text:
        return False

    config = _get_config()
    return config.has_prefix(text)


def normalize_command(command: str) -> str:
    return command.lower().strip()


def is_valid_command(command: str) -> bool:
    config = _get_config()
    return config.is_valid_command(command)


def get_enabled_prefixes() -> list[str]:
    config = _get_config()
    return config.enabled_prefixes


def get_valid_command_names() -> set[str]:
    config = _get_config()
    return config.valid_command_names
