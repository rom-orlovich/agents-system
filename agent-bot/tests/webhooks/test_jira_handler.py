import pytest
import json
import hmac
import hashlib
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api-gateway"))

from webhooks.handlers.jira import JiraWebhookHandler
from webhooks.registry.protocol import PayloadParseError


@pytest.fixture
def handler():
    return JiraWebhookHandler()


@pytest.fixture
def jira_payload():
    return {
        "webhookEvent": "jira:issue_created",
        "issue_event_type_name": "issue_created",
        "user": {
            "accountId": "test-account-123",
            "displayName": "Test User",
        },
        "issue": {
            "id": "10001",
            "key": "PROJ-123",
            "fields": {
                "issuetype": {"name": "Bug"},
                "summary": "Test issue",
                "description": "Test description @agent please analyze",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "assignee": {"displayName": "Agent Bot"},
                "project": {
                    "key": "PROJ",
                    "name": "Test Project",
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_validate_with_valid_signature(handler, jira_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(jira_payload).encode()

    signature = "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()

    headers = {"x-hub-signature": signature}

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is True


@pytest.mark.asyncio
async def test_validate_with_invalid_signature(handler, jira_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(jira_payload).encode()

    headers = {"x-hub-signature": "sha256=invalid"}

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is False


@pytest.mark.asyncio
async def test_validate_missing_signature(handler, jira_payload):
    secret = "test-secret"
    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    result = await handler.validate(payload_bytes, headers, secret)
    assert result is False


@pytest.mark.asyncio
async def test_parse_issue_created(handler, jira_payload):
    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)

    assert webhook_payload.provider == "jira"
    assert webhook_payload.event_type == "issue_created"
    assert webhook_payload.installation_id == "test-account-123"
    assert webhook_payload.organization_id == "PROJ"
    assert webhook_payload.metadata["issue_key"] == "PROJ-123"
    assert webhook_payload.metadata["summary"] == "Test issue"
    assert webhook_payload.metadata["priority"] == "High"


@pytest.mark.asyncio
async def test_parse_invalid_json(handler):
    payload_bytes = b"invalid json"
    headers = {}

    with pytest.raises(PayloadParseError):
        await handler.parse(payload_bytes, headers)


@pytest.mark.asyncio
async def test_should_process_with_agent_mention(handler, jira_payload):
    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is True


@pytest.mark.asyncio
async def test_should_process_with_agent_assigned(handler, jira_payload):
    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is True


@pytest.mark.asyncio
async def test_should_process_without_triggers(handler, jira_payload):
    jira_payload["issue"]["fields"]["description"] = "Regular description"
    jira_payload["issue"]["fields"]["assignee"] = {"displayName": "Human User"}
    jira_payload["issue"]["fields"]["priority"] = {"name": "Low"}

    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    result = await handler.should_process(webhook_payload)

    assert result is False


@pytest.mark.asyncio
async def test_create_task_request(handler, jira_payload):
    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.provider == "jira"
    assert task_request.installation_id == "test-account-123"
    assert task_request.priority == 1
    assert "please analyze" in task_request.input_message


@pytest.mark.asyncio
async def test_priority_mapping(handler, jira_payload):
    jira_payload["issue"]["fields"]["priority"] = {"name": "Highest"}

    payload_bytes = json.dumps(jira_payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.priority == 0
