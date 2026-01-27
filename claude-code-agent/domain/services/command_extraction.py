"""
Command extraction from text.

This module provides unified command extraction logic for:
- @agent <command> <content> format
- /agent <command> <content> format

Used by all webhook handlers to extract commands from:
- GitHub comments
- Jira comments
- Slack messages
"""

import re
from typing import Optional, Tuple

# Command prefixes that trigger the agent
COMMAND_PREFIXES = ("@agent", "/agent", "@claude", "/claude")

# Regex pattern for extracting command and content
# Matches: @agent <command> [optional content]
# Groups: 1=prefix, 2=command, 3=content
COMMAND_PATTERN = re.compile(
    r"(?:^|\s)(@agent|/agent|@claude|/claude)\s+(\w+)(?:\s+(.*))?",
    re.IGNORECASE | re.DOTALL
)


def extract_command(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract command and content from text.

    Looks for patterns like:
    - @agent review this code
    - /agent implement the feature
    - @claude help

    Args:
        text: Text to extract command from

    Returns:
        Tuple of (command, content) if found, None otherwise
        command is lowercase, content may be empty string

    Examples:
        >>> extract_command("@agent review this code")
        ('review', 'this code')
        >>> extract_command("Hello @agent help please")
        ('help', 'please')
        >>> extract_command("No command here")
        None
    """
    if not text:
        return None

    match = COMMAND_PATTERN.search(text)
    if not match:
        return None

    command = match.group(2).lower()
    content = (match.group(3) or "").strip()

    return (command, content)


def extract_command_with_prefix(text: str) -> Optional[Tuple[str, str, str]]:
    """
    Extract prefix, command, and content from text.

    Like extract_command but also returns the prefix used.

    Args:
        text: Text to extract command from

    Returns:
        Tuple of (prefix, command, content) if found, None otherwise

    Examples:
        >>> extract_command_with_prefix("@agent review code")
        ('@agent', 'review', 'code')
    """
    if not text:
        return None

    match = COMMAND_PATTERN.search(text)
    if not match:
        return None

    prefix = match.group(1).lower()
    command = match.group(2).lower()
    content = (match.group(3) or "").strip()

    return (prefix, command, content)


def has_agent_mention(text: str) -> bool:
    """
    Check if text contains an agent mention.

    Faster than extract_command when you only need to check presence.

    Args:
        text: Text to check

    Returns:
        True if text contains @agent or similar prefix
    """
    if not text:
        return False

    text_lower = text.lower()
    return any(prefix in text_lower for prefix in COMMAND_PREFIXES)


def normalize_command(command: str) -> str:
    """
    Normalize a command name.

    Converts to lowercase and handles common variations.

    Args:
        command: Command to normalize

    Returns:
        Normalized command name
    """
    return command.lower().strip()
