"""
Shared webhook validation utilities.
Common functions and models used across all webhook handlers.
"""

import re
from typing import Optional
from pydantic import BaseModel


VALID_COMMANDS = {"analyze", "plan", "fix", "review", "approve", "reject", "improve", "help", "discover"}


class WebhookValidationResult(BaseModel):
    """Result of webhook validation."""
    is_valid: bool
    error_message: str = ""

    @classmethod
    def success(cls) -> "WebhookValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True)

    @classmethod
    def failure(cls, error_message: str) -> "WebhookValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, error_message=error_message)


def extract_command(text: str) -> Optional[str]:
    """Extract @agent command from text."""
    # Defensive type conversion to prevent TypeError with regex
    if text is None:
        return None
    if isinstance(text, list):
        text = " ".join(str(item) for item in text if item)
    elif not isinstance(text, str):
        text = str(text) if text else ""

    if not text:
        return None

    match = re.search(r"@agent\s+(\w+)", text, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def validate_command(command: Optional[str]) -> tuple[bool, str]:
    """Validate that command is in the allowed list."""
    if not command:
        return False, "No @agent prefix found"
    if command not in VALID_COMMANDS:
        return False, f"@agent found but invalid command: {command}"
    return True, ""
