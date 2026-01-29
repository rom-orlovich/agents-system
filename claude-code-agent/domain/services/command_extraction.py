import re
from typing import Optional, Tuple

COMMAND_PREFIXES = ("@agent", "/agent", "@claude", "/claude")

COMMAND_PATTERN = re.compile(
    r"(?:^|\s)(@agent|/agent|@claude|/claude)\s+(\w+)(?:\s+(.*))?",
    re.IGNORECASE | re.DOTALL
)


def extract_command(text: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None

    match = COMMAND_PATTERN.search(text)
    if not match:
        return None

    command = match.group(2).lower()
    content = (match.group(3) or "").strip()

    return (command, content)


def extract_command_with_prefix(text: str) -> Optional[Tuple[str, str, str]]:
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
    if not text:
        return False

    text_lower = text.lower()
    return any(prefix in text_lower for prefix in COMMAND_PREFIXES)


def normalize_command(command: str) -> str:
    return command.lower().strip()
