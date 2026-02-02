"""Slack webhook payload fixtures for testing."""

from typing import Any


def slack_app_mention_payload(
    channel: str = "C1234567890",
    user: str = "U1234567890",
    text: str = "<@U0BOTUSER> help me fix this bug",
    thread_ts: str | None = None,
    event_ts: str = "1706702400.000001",
    team: str = "T1234567890",
) -> dict[str, Any]:
    """Create a Slack app mention event payload."""
    event: dict[str, Any] = {
        "type": "app_mention",
        "channel": channel,
        "user": user,
        "text": text,
        "ts": event_ts,
        "event_ts": event_ts,
    }

    if thread_ts:
        event["thread_ts"] = thread_ts

    return {
        "token": "verification-token",
        "team_id": team,
        "api_app_id": "A1234567890",
        "event": event,
        "type": "event_callback",
        "event_id": "Ev1234567890",
        "event_time": 1706702400,
        "authorizations": [
            {
                "enterprise_id": None,
                "team_id": team,
                "user_id": "U0BOTUSER",
                "is_bot": True,
            }
        ],
    }


def slack_message_payload(
    channel: str = "C1234567890",
    user: str = "U1234567890",
    text: str = "Hello, this is a test message",
    thread_ts: str | None = None,
    event_ts: str = "1706702400.000001",
    team: str = "T1234567890",
    subtype: str | None = None,
    bot_id: str | None = None,
) -> dict[str, Any]:
    """Create a Slack message event payload."""
    event: dict[str, Any] = {
        "type": "message",
        "channel": channel,
        "user": user,
        "text": text,
        "ts": event_ts,
        "event_ts": event_ts,
    }

    if thread_ts:
        event["thread_ts"] = thread_ts

    if subtype:
        event["subtype"] = subtype

    if bot_id:
        event["bot_id"] = bot_id
        del event["user"]

    return {
        "token": "verification-token",
        "team_id": team,
        "api_app_id": "A1234567890",
        "event": event,
        "type": "event_callback",
        "event_id": "Ev1234567890",
        "event_time": 1706702400,
    }


def slack_url_verification_payload(
    challenge: str = "test-challenge-token",
) -> dict[str, Any]:
    """Create a Slack URL verification payload."""
    return {
        "token": "verification-token",
        "challenge": challenge,
        "type": "url_verification",
    }


def slack_bot_message_payload(
    channel: str = "C1234567890",
    bot_id: str = "B1234567890",
    text: str = "Bot response message",
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """Create a Slack bot message payload (should be ignored)."""
    return slack_message_payload(
        channel=channel,
        user="",
        text=text,
        thread_ts=thread_ts,
        subtype="bot_message",
        bot_id=bot_id,
    )
