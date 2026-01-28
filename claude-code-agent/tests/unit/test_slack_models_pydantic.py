import pytest
from pydantic import ValidationError, TypeAdapter
from api.webhooks.slack.models import (
    SlackUser,
    SlackTeam,
    SlackChannel,
    SlackMessage,
    SlackEventCallback,
    SlackUrlVerification,
    SlackAppMentionEvent,
    SlackMessageEvent,
    SlackSlashCommand,
    SlackWebhookPayload,
)

SlackPayloadAdapter = TypeAdapter(SlackWebhookPayload)


class TestSlackUser:
    def test_valid_user(self):
        user_data = {"id": "U123ABC", "username": "testuser", "name": "Test User"}
        user = SlackUser(**user_data)
        assert user.id == "U123ABC"
        assert user.username == "testuser"
        assert user.name == "Test User"

    def test_user_missing_required_fields(self):
        user_data = {"id": "U123ABC"}
        with pytest.raises(ValidationError) as exc_info:
            SlackUser(**user_data)
        assert "username" in str(exc_info.value)


class TestSlackTeam:
    def test_valid_team(self):
        team_data = {"id": "T123ABC", "domain": "test-workspace"}
        team = SlackTeam(**team_data)
        assert team.id == "T123ABC"
        assert team.domain == "test-workspace"

    def test_team_missing_id(self):
        team_data = {"domain": "test-workspace"}
        with pytest.raises(ValidationError) as exc_info:
            SlackTeam(**team_data)
        assert "id" in str(exc_info.value)


class TestSlackChannel:
    def test_valid_channel(self):
        channel_data = {"id": "C123ABC", "name": "general"}
        channel = SlackChannel(**channel_data)
        assert channel.id == "C123ABC"
        assert channel.name == "general"

    def test_channel_missing_name(self):
        channel_data = {"id": "C123ABC"}
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(**channel_data)
        assert "name" in str(exc_info.value)


class TestSlackMessage:
    def test_valid_message(self):
        message_data = {
            "type": "message",
            "user": "U123ABC",
            "text": "Hello, world!",
            "ts": "1609459200.000100",
        }
        message = SlackMessage(**message_data)
        assert message.type == "message"
        assert message.text == "Hello, world!"
        assert message.user == "U123ABC"

    def test_message_missing_text(self):
        message_data = {"type": "message", "user": "U123ABC", "ts": "1609459200.000100"}
        with pytest.raises(ValidationError) as exc_info:
            SlackMessage(**message_data)
        assert "text" in str(exc_info.value)


class TestSlackAppMentionEvent:
    def test_valid_app_mention(self):
        event_data = {
            "type": "app_mention",
            "user": "U123ABC",
            "text": "<@U456DEF> analyze this issue",
            "ts": "1609459200.000100",
            "channel": "C123ABC",
        }
        event = SlackAppMentionEvent(**event_data)
        assert event.type == "app_mention"
        assert event.text == "<@U456DEF> analyze this issue"
        assert event.channel == "C123ABC"

    def test_app_mention_text_extraction(self):
        event_data = {
            "type": "app_mention",
            "user": "U123ABC",
            "text": "<@U456DEF> review the PR",
            "ts": "1609459200.000100",
            "channel": "C123ABC",
        }
        event = SlackAppMentionEvent(**event_data)
        text = event.extract_text()
        assert text == "<@U456DEF> review the PR"


class TestSlackMessageEvent:
    def test_valid_message_event(self):
        event_data = {
            "type": "message",
            "user": "U123ABC",
            "text": "This is a message",
            "ts": "1609459200.000100",
            "channel": "C123ABC",
        }
        event = SlackMessageEvent(**event_data)
        assert event.type == "message"
        assert event.text == "This is a message"

    def test_message_event_text_extraction(self):
        event_data = {
            "type": "message",
            "user": "U123ABC",
            "text": "Message content here",
            "ts": "1609459200.000100",
            "channel": "C123ABC",
        }
        event = SlackMessageEvent(**event_data)
        text = event.extract_text()
        assert text == "Message content here"


class TestSlackEventCallback:
    def test_valid_event_callback_app_mention(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "api_app_id": "A123ABC",
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123ABC",
                "text": "<@U456DEF> help",
                "ts": "1609459200.000100",
                "channel": "C123ABC",
            },
        }
        payload = SlackEventCallback(**payload_data)
        assert payload.type == "event_callback"
        assert payload.event.type == "app_mention"
        assert payload.event.text == "<@U456DEF> help"

    def test_valid_event_callback_message(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "api_app_id": "A123ABC",
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123ABC",
                "text": "Hello",
                "ts": "1609459200.000100",
                "channel": "C123ABC",
            },
        }
        payload = SlackEventCallback(**payload_data)
        assert payload.type == "event_callback"
        assert payload.event.type == "message"

    def test_event_callback_text_extraction(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "api_app_id": "A123ABC",
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123ABC",
                "text": "Event text content",
                "ts": "1609459200.000100",
                "channel": "C123ABC",
            },
        }
        payload = SlackEventCallback(**payload_data)
        text = payload.extract_text()
        assert text == "Event text content"


class TestSlackUrlVerification:
    def test_valid_url_verification(self):
        payload_data = {"type": "url_verification", "challenge": "challenge_string"}
        payload = SlackUrlVerification(**payload_data)
        assert payload.type == "url_verification"
        assert payload.challenge == "challenge_string"

    def test_url_verification_missing_challenge(self):
        payload_data = {"type": "url_verification"}
        with pytest.raises(ValidationError) as exc_info:
            SlackUrlVerification(**payload_data)
        assert "challenge" in str(exc_info.value)


class TestSlackSlashCommand:
    def test_valid_slash_command(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "team_domain": "test-workspace",
            "channel_id": "C123ABC",
            "channel_name": "general",
            "user_id": "U123ABC",
            "user_name": "testuser",
            "command": "/agent",
            "text": "analyze issue",
            "response_url": "https://hooks.slack.com/commands/123/456",
            "trigger_id": "123.456",
        }
        payload = SlackSlashCommand(**payload_data)
        assert payload.command == "/agent"
        assert payload.text == "analyze issue"
        assert payload.user_name == "testuser"

    def test_slash_command_text_extraction(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "team_domain": "test-workspace",
            "channel_id": "C123ABC",
            "channel_name": "general",
            "user_id": "U123ABC",
            "user_name": "testuser",
            "command": "/agent",
            "text": "review the code",
            "response_url": "https://hooks.slack.com/commands/123/456",
            "trigger_id": "123.456",
        }
        payload = SlackSlashCommand(**payload_data)
        text = payload.extract_text()
        assert text == "review the code"

    def test_slash_command_missing_command(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "team_domain": "test-workspace",
            "channel_id": "C123ABC",
            "channel_name": "general",
            "user_id": "U123ABC",
            "user_name": "testuser",
            "text": "analyze issue",
            "response_url": "https://hooks.slack.com/commands/123/456",
            "trigger_id": "123.456",
        }
        with pytest.raises(ValidationError) as exc_info:
            SlackSlashCommand(**payload_data)
        assert "command" in str(exc_info.value)


class TestSlackWebhookPayload:
    def test_discriminated_union_event_callback(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "api_app_id": "A123ABC",
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123ABC",
                "text": "<@U456DEF> help",
                "ts": "1609459200.000100",
                "channel": "C123ABC",
            },
        }
        payload = SlackPayloadAdapter.validate_python(payload_data)
        assert isinstance(payload, SlackEventCallback)
        assert payload.event.text == "<@U456DEF> help"

    def test_discriminated_union_url_verification(self):
        payload_data = {"type": "url_verification", "challenge": "challenge_string"}
        payload = SlackPayloadAdapter.validate_python(payload_data)
        assert isinstance(payload, SlackUrlVerification)
        assert payload.challenge == "challenge_string"

    def test_discriminated_union_slash_command(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "team_domain": "test-workspace",
            "channel_id": "C123ABC",
            "channel_name": "general",
            "user_id": "U123ABC",
            "user_name": "testuser",
            "command": "/agent",
            "text": "analyze",
            "response_url": "https://hooks.slack.com/commands/123/456",
            "trigger_id": "123.456",
        }
        payload = SlackPayloadAdapter.validate_python(payload_data)
        assert isinstance(payload, SlackSlashCommand)
        assert payload.text == "analyze"

    def test_text_extraction_from_event_callback(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "api_app_id": "A123ABC",
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U123ABC",
                "text": "Extracted text",
                "ts": "1609459200.000100",
                "channel": "C123ABC",
            },
        }
        payload = SlackPayloadAdapter.validate_python(payload_data)
        text = payload.extract_text()
        assert text == "Extracted text"

    def test_text_extraction_from_slash_command(self):
        payload_data = {
            "token": "verification_token",
            "team_id": "T123ABC",
            "team_domain": "test-workspace",
            "channel_id": "C123ABC",
            "channel_name": "general",
            "user_id": "U123ABC",
            "user_name": "testuser",
            "command": "/agent",
            "text": "Command text",
            "response_url": "https://hooks.slack.com/commands/123/456",
            "trigger_id": "123.456",
        }
        payload = SlackPayloadAdapter.validate_python(payload_data)
        text = payload.extract_text()
        assert text == "Command text"

    def test_validation_error_invalid_type(self):
        payload_data = {"type": "invalid_type", "some_field": "some_value"}
        with pytest.raises(ValidationError):
            SlackPayloadAdapter.validate_python(payload_data)
