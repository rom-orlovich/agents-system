from typing import Optional

BOT_SUFFIXES = ("[bot]",)

BOT_USER_TYPES = ("bot",)

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
    if bot_id:
        return True

    if user_type and user_type.lower() in BOT_USER_TYPES:
        return True

    if login:
        login_lower = login.lower()

        for suffix in BOT_SUFFIXES:
            if login_lower.endswith(suffix):
                return True

        if login_lower in KNOWN_BOTS:
            return True

    return False


def is_github_bot(sender_login: str, sender_type: str) -> bool:
    return is_bot(login=sender_login, user_type=sender_type)


def is_slack_bot(event: dict) -> bool:
    if event.get("bot_id"):
        return True

    if event.get("subtype") == "bot_message":
        return True

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
    if is_bot(login=login, user_type=user_type):
        return True

    return False
