import pytest
import json
import hmac
import hashlib
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api-gateway"))

from webhooks.handlers.slack import SlackWebhookHandler
from webhooks.registry.protocol import PayloadParseError


@pytest.fixture
def handler():
    return SlackWebhookHandler()


@pytest.fixture
def slack_message_payload():
    return {
        "type": "event_callback",
        "team_id": "T123456",
        "event": {
            "type": "message",
            "channel": "C123456",
            "channel_type": "channel",
            "user": "U123456",
            "text": "@agent help me with this",
            "ts": "1234567890.123456",
        },
    }


@pytest.fixture
def slack_mention_payload():
    return {
        "type": "event_callback",
        "team_id": "T123456",
        "event": {
            "type": "app_mention",
            "channel": "C123456",
            "channel_type": "channel",
            "user": "U123456",
            "text": "<@UAGENT123> can you review this code?",
            "ts": "1234567890.123456",
            "thread_ts": "1234567890.000000",
        },
    }


@pytest.mark.asyncio
async def test_validate_with_valid_signature(handler, slack_message_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(slack_message_payload).encode()
    timestamp = "1234567890"

    sig_basestring = f"v0:{timestamp}:{payload_bytes.decode()}"
    signature = "v0=" + hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()

    headers = {
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": signature,
    }

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is True


@pytest.mark.asyncio
async def test_validate_with_invalid_signature(handler, slack_message_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(slack_message_payload).encode()

    headers = {
        "x-slack-request-timestamp": "1234567890",
        "x-slack-signature": "v0=invalid",
    }

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is False


@pytest.mark.asyncio
async def test_validate_missing_headers(handler, slack_message_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(slack_message_payload).encode()
    headers = {}

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is False


@pytest.mark.asyncio
async def test_parse_message_event(handler, slack_message_payload):
    payload_bytes = json.dumps(slack_message_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)

    assert webhook_payload.provider == "slack"
    assert webhook_payload.event_type == "message"
    assert webhook_payload.installation_id == "T123456"
    assert webhook_payload.metadata["channel"] == "C123456"
    assert webhook_payload.metadata["user"] == "U123456"
    assert "@agent" in webhook_payload.metadata["text"]


@pytest.mark.asyncio
async def test_parse_app_mention(handler, slack_mention_payload):
    payload_bytes = json.dumps(slack_mention_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)

    assert webhook_payload.event_type == "app_mention"
    assert webhook_payload.metadata["thread_ts"] == "1234567890.000000"


@pytest.mark.asyncio
async def test_should_process_with_mention(handler, slack_mention_payload):
    payload_bytes = json.dumps(slack_mention_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is True


@pytest.mark.asyncio
async def test_should_process_with_keyword(handler, slack_message_payload):
    payload_bytes = json.dumps(slack_message_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is True


@pytest.mark.asyncio
async def test_should_process_bot_message(handler, slack_message_payload):
    slack_message_payload["event"]["bot_id"] = "B123456"

    payload_bytes = json.dumps(slack_message_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is False


@pytest.mark.asyncio
async def test_create_task_request(handler, slack_mention_payload):
    payload_bytes = json.dumps(slack_mention_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.provider == "slack"
    assert task_request.installation_id == "T123456"
    assert "review this code" in task_request.input_message.lower()


@pytest.mark.asyncio
async def test_extract_input_message_removes_mention(handler, slack_mention_payload):
    payload_bytes = json.dumps(slack_mention_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    task_request = await handler.create_task_request(webhook_payload)

    assert "<@UAGENT123>" not in task_request.input_message
    assert "can you review this code?" in task_request.input_message
