"""Tests for Slack webhook business logic.

Tests processing of Slack events.
"""

from .fixtures import (
    slack_app_mention_payload,
    slack_message_payload,
    slack_url_verification_payload,
)


def is_bot_message(payload: dict) -> bool:
    """Check if message is from a bot."""
    event = payload.get("event", {})
    return "bot_id" in event or event.get("subtype") == "bot_message"


def should_process_slack_event(event_type: str, payload: dict) -> bool:
    """Determine if Slack event should be processed."""
    if payload.get("type") == "url_verification":
        return True

    event = payload.get("event", {})
    actual_event_type = event.get("type")

    if is_bot_message(payload):
        return False

    supported_events = ["app_mention", "message"]
    return actual_event_type in supported_events


def extract_slack_task_info(payload: dict) -> dict:
    """Extract task info from Slack payload."""
    event = payload.get("event", {})

    task_info = {
        "source": "slack",
        "event_type": event.get("type"),
        "channel": event.get("channel"),
        "user": event.get("user"),
        "text": event.get("text"),
        "ts": event.get("ts"),
        "team_id": payload.get("team_id"),
    }

    if "thread_ts" in event:
        task_info["thread_ts"] = event["thread_ts"]

    return task_info


class TestSlackEventProcessing:
    """Tests for Slack event processing."""

    def test_app_mention_creates_task(self):
        """Business requirement: @agent mentions trigger."""
        payload = slack_app_mention_payload(
            channel="C1234567890",
            user="U1234567890",
            text="<@U0BOTUSER> help me fix this bug",
        )

        assert should_process_slack_event("app_mention", payload) is True

    def test_direct_message_creates_task(self):
        """Business requirement: DM to bot works."""
        payload = slack_message_payload(
            channel="D1234567890",
            user="U1234567890",
            text="Please analyze this code",
        )

        assert should_process_slack_event("message", payload) is True

    def test_bot_own_message_ignored(self):
        """Business requirement: Prevent self-response loops."""
        payload = slack_message_payload(
            channel="C1234567890",
            user="",
            text="Bot response",
            bot_id="B1234567890",
        )

        assert should_process_slack_event("message", payload) is False

    def test_bot_message_subtype_ignored(self):
        """Business requirement: Bot message subtypes ignored."""
        payload = slack_message_payload(
            channel="C1234567890",
            user="",
            text="Bot response",
            subtype="bot_message",
        )

        assert should_process_slack_event("message", payload) is False

    def test_url_verification_handled(self):
        """Business requirement: URL verification for setup."""
        payload = slack_url_verification_payload(challenge="test-challenge")

        assert should_process_slack_event("url_verification", payload) is True


class TestSlackTaskExtraction:
    """Tests for extracting task info from Slack payloads."""

    def test_task_contains_slack_context(self):
        """Business requirement: Reply context preserved."""
        payload = slack_app_mention_payload(
            channel="C1234567890",
            user="U1234567890",
            text="<@U0BOTUSER> help",
            thread_ts="1706702300.000001",
        )

        task_info = extract_slack_task_info(payload)

        assert task_info["source"] == "slack"
        assert task_info["channel"] == "C1234567890"
        assert task_info["user"] == "U1234567890"
        assert task_info["thread_ts"] == "1706702300.000001"

    def test_message_without_thread(self):
        """Message without thread_ts is valid."""
        payload = slack_app_mention_payload(
            channel="C1234567890",
            user="U1234567890",
            text="<@U0BOTUSER> quick question",
        )

        task_info = extract_slack_task_info(payload)

        assert "thread_ts" not in task_info
        assert task_info["text"] == "<@U0BOTUSER> quick question"

    def test_team_id_extracted(self):
        """Team ID preserved for multi-workspace support."""
        payload = slack_app_mention_payload(
            team="T9876543210",
        )

        task_info = extract_slack_task_info(payload)

        assert task_info["team_id"] == "T9876543210"


class TestBotMessageDetection:
    """Tests for bot message detection."""

    def test_message_with_bot_id_is_bot(self):
        """Messages with bot_id are bot messages."""
        payload = slack_message_payload(bot_id="B1234567890", user="")
        assert is_bot_message(payload) is True

    def test_message_with_bot_subtype_is_bot(self):
        """Messages with bot_message subtype are bot messages."""
        payload = slack_message_payload(subtype="bot_message", user="")
        assert is_bot_message(payload) is True

    def test_regular_user_message_is_not_bot(self):
        """Regular user messages are not bot messages."""
        payload = slack_message_payload(user="U1234567890")
        assert is_bot_message(payload) is False


class TestSlackEventTypes:
    """Tests for supported Slack event types."""

    def test_supported_slack_events(self):
        """Verify supported Slack events."""
        mention_payload = slack_app_mention_payload()
        message_payload = slack_message_payload()

        assert should_process_slack_event("app_mention", mention_payload) is True
        assert should_process_slack_event("message", message_payload) is True

    def test_url_verification_always_processed(self):
        """URL verification always returns True."""
        payload = slack_url_verification_payload()
        assert should_process_slack_event("url_verification", payload) is True
