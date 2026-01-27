"""
Shared command matching logic for all webhooks.
DETERMINISTIC CODE - NOT LLM-based.
"""
import re
from typing import Optional, Tuple
from core.config import settings
from core.github_client import github_client


def is_bot_comment(sender_login: str, sender_type: str) -> bool:
    if not isinstance(sender_login, str):
        sender_login = str(sender_login) if sender_login else ""
    if not isinstance(sender_type, str):
        if isinstance(sender_type, list):
            sender_type = " ".join(str(item) for item in sender_type if item)
        else:
            sender_type = str(sender_type) if sender_type else ""
    
    sender_lower = sender_login.lower()
    sender_type_lower = sender_type.lower()

    if "bot" in sender_type_lower:
        return True

    if "[bot]" in sender_lower:
        return True

    if sender_lower in settings.bot_usernames_list:
        return True

    return False


def extract_command(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract command from text following format: @agent <command> [user-content]

    Args:
        text: The text to extract command from (comment body, issue description, etc.)

    Returns:
        Tuple of (command_name, user_content) if valid command found
        None if no valid command

    Example:
        extract_command("@agent review please check the scroll button")
        -> ("review", "please check the scroll button")
    """
    if not text:
        return None
    
    if not isinstance(text, str):
        try:
            if isinstance(text, list):
                text = " ".join(str(item) for item in text if item)
            else:
                text = str(text)
        except Exception:
            return None
    
    if not text:
        return None

    prefix = settings.webhook_agent_prefix.lower()
    text_lower = text.lower()

    # Must contain the prefix
    if prefix not in text_lower:
        return None

    # Extract word immediately after @agent
    # Pattern: @agent\s+(\w+)(.*)
    pattern = rf'{re.escape(prefix)}\s+(\w+)(.*)'
    match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)

    if not match:
        return None

    command_word = match.group(1).lower()

    # Validate against configured valid commands
    if command_word not in settings.valid_commands_list:
        return None

    # Get the original case user content from original text
    original_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if original_match:
        user_content = original_match.group(2).strip()
    else:
        user_content = ""

    return (command_word, user_content)


async def is_agent_own_comment(sender_login: str, sender_type: str) -> bool:
    """
    Check if comment is from the agent's own GitHub account.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        sender_login: Username/login of the sender
        sender_type: Type field from the API (e.g., "Bot", "User")
    
    Returns:
        True if this is the agent's own comment (should be skipped), False otherwise
    """
    if not sender_login:
        return False
    
    authenticated_user = await github_client.get_authenticated_user()
    if not authenticated_user:
        return False
    
    sender_lower = sender_login.lower()
    authenticated_lower = authenticated_user.lower()
    
    if sender_lower == authenticated_lower:
        return True
    
    return False
