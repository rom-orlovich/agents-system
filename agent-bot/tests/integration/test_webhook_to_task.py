import pytest
import json
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api-gateway"))

from webhooks.handlers.github import GitHubWebhookHandler
from webhooks.handlers.jira import JiraWebhookHandler
from webhooks.handlers.slack import SlackWebhookHandler
from webhooks.registry.registry import WebhookRegistry


@pytest.fixture
def registry():
    reg = WebhookRegistry()
    reg.register("github", GitHubWebhookHandler())
    reg.register("jira", JiraWebhookHandler())
    reg.register("slack", SlackWebhookHandler())
    return reg


@pytest.mark.asyncio
async def test_github_webhook_to_task_flow(registry):
    handler = registry.get_handler("github")
    assert handler is not None

    payload = {
        "action": "opened",
        "installation": {"id": 12345},
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 42,
            "title": "Add new feature",
            "body": "@agent please review",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123",
            },
        },
    }

    payload_bytes = json.dumps(payload).encode()
    headers = {"x-github-event": "pull_request"}

    webhook_payload = await handler.parse(payload_bytes, headers)
    should_process = await handler.should_process(webhook_payload)
    assert should_process is True

    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.provider == "github"
    assert task_request.installation_id == "12345"
    assert task_request.source_metadata["pr_number"] == "42"
    assert task_request.priority >= 0


@pytest.mark.asyncio
async def test_jira_webhook_to_task_flow(registry):
    handler = registry.get_handler("jira")
    assert handler is not None

    payload = {
        "webhookEvent": "jira:issue_created",
        "user": {"accountId": "user-123"},
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Critical bug",
                "description": "@agent analyze this",
                "priority": {"name": "Highest"},
                "status": {"name": "Open"},
                "issuetype": {"name": "Bug"},
                "project": {"key": "PROJ", "name": "Project"},
            },
        },
    }

    payload_bytes = json.dumps(payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    should_process = await handler.should_process(webhook_payload)
    assert should_process is True

    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.provider == "jira"
    assert task_request.source_metadata["issue_key"] == "PROJ-123"
    assert task_request.priority == 0


@pytest.mark.asyncio
async def test_slack_webhook_to_task_flow(registry):
    handler = registry.get_handler("slack")
    assert handler is not None

    payload = {
        "type": "event_callback",
        "team_id": "T123",
        "event": {
            "type": "app_mention",
            "channel": "C123",
            "channel_type": "channel",
            "user": "U123",
            "text": "<@UAGENT> help with this issue",
            "ts": "1234567890.123",
        },
    }

    payload_bytes = json.dumps(payload).encode()
    headers = {}

    webhook_payload = await handler.parse(payload_bytes, headers)
    should_process = await handler.should_process(webhook_payload)
    assert should_process is True

    task_request = await handler.create_task_request(webhook_payload)

    assert task_request.provider == "slack"
    assert task_request.source_metadata["channel"] == "C123"


@pytest.mark.asyncio
async def test_registry_lists_all_providers(registry):
    providers = registry.list_providers()

    assert "github" in providers
    assert "jira" in providers
    assert "slack" in providers
    assert len(providers) == 3


@pytest.mark.asyncio
async def test_registry_has_handler(registry):
    assert registry.has_handler("github") is True
    assert registry.has_handler("jira") is True
    assert registry.has_handler("slack") is True
    assert registry.has_handler("unknown") is False
