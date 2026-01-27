"""
Bot detection utilities.

This module provides logic to detect if a user/sender is a bot,
used to prevent infinite loops when the agent responds to its own messages.

Consolidates bot detection from:
- github/utils.py: is_bot_comment logic
- slack/utils.py: bot message detection
"""

from typing import Optional

# Known bot suffixes
BOT_SUFFIXES = ("[bot]",)

# Known bot user types (case-insensitive)
BOT_USER_TYPES = ("bot",)

# Known bot usernames to ignore
KNOWN_BOTS = (
    "github-actions[bot]",
    "dependabot[bot]",
    "dependabot-preview[bot]",
    "renovate[bot]",
    "codecov[bot]",
    "sonarcloud[bot]",
    "mergify[bot]",
    "semantic-release-bot",
    "greenkeeper[bot]",
    "snyk-bot",
    "allcontributors[bot]",
)


def is_bot(
    login: Optional[str] = None,
    user_type: Optional[str] = None,
    bot_id: Optional[str] = None,
) -> bool:
    """
    Check if a user is a bot.

    Detection is based on:
    1. User type is "Bot" (case-insensitive)
    2. Login ends with "[bot]" (case-insensitive)
    3. Login is in known bots list
    4. bot_id is present (Slack)

    Args:
        login: Username/login (e.g., "github-actions[bot]")
        user_type: User type (e.g., "Bot", "User")
        bot_id: Bot ID (Slack-specific)

    Returns:
        True if user is detected as a bot

    Examples:
        >>> is_bot(login="github-actions[bot]", user_type="Bot")
        True
        >>> is_bot(login="john-doe", user_type="User")
        False
        >>> is_bot(bot_id="B12345")
        True
    """
    # Check Slack bot_id
    if bot_id:
        return True

    # Check user type
    if user_type and user_type.lower() in BOT_USER_TYPES:
        return True

    # Check login
    if login:
        login_lower = login.lower()

        # Check for bot suffix
        for suffix in BOT_SUFFIXES:
            if login_lower.endswith(suffix):
                return True

        # Check known bots
        if login_lower in KNOWN_BOTS:
            return True

    return False


def is_github_bot(sender_login: str, sender_type: str) -> bool:
    """
    Check if a GitHub sender is a bot.

    Convenience wrapper for GitHub-specific bot detection.

    Args:
        sender_login: GitHub username
        sender_type: GitHub user type

    Returns:
        True if sender is a bot
    """
    return is_bot(login=sender_login, user_type=sender_type)


def is_slack_bot(event: dict) -> bool:
    """
    Check if a Slack event is from a bot.

    Args:
        event: Slack event object

    Returns:
        True if event is from a bot
    """
    # Check for bot_id in event
    if event.get("bot_id"):
        return True

    # Check for bot_message subtype
    if event.get("subtype") == "bot_message":
        return True

    # Check user type
    user = event.get("user", {})
    if isinstance(user, dict):
        if user.get("is_bot"):
            return True

    return False


def should_skip_comment(
    login: Optional[str] = None,
    user_type: Optional[str] = None,
    comment_body: Optional[str] = None,
) -> bool:
    """
    Check if a comment should be skipped (from bot or agent response).

    Args:
        login: Username of commenter
        user_type: User type
        comment_body: Comment text (for additional checks)

    Returns:
        True if comment should be skipped
    """
    # Skip bot comments
    if is_bot(login=login, user_type=user_type):
        return True

    # Additional checks could be added here
    # e.g., checking if comment matches agent response patterns

    return False
