"""
Shared webhook validation utilities.
Common functions and models used across all webhook handlers.
"""

from typing import Optional
from pydantic import BaseModel
from domain.models.commands import get_commands_config


class WebhookValidationResult(BaseModel):
    is_valid: bool
    error_message: str = ""

    @classmethod
    def success(cls) -> "WebhookValidationResult":
        return cls(is_valid=True)

    @classmethod
    def failure(cls, error_message: str) -> "WebhookValidationResult":
        return cls(is_valid=False, error_message=error_message)


def get_valid_commands() -> set[str]:
    config = get_commands_config()
    return config.valid_command_names


def extract_command(text: str) -> Optional[str]:
    config = get_commands_config()
    match = config.command_pattern.search(text)
    if match:
        return match.group(2).lower()
    return None


def validate_command(command: Optional[str]) -> tuple[bool, str]:
    config = get_commands_config()
    if not command:
        prefixes = ", ".join(config.enabled_prefixes)
        return False, f"No agent prefix found (valid: {prefixes})"
    if not config.is_valid_command(command):
        valid_cmds = ", ".join(sorted(config.valid_command_names))
        return False, f"Invalid command: {command}. Valid commands: {valid_cmds}"
    return True, ""
