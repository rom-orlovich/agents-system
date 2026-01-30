import pytest
import hmac
import hashlib
import json
from datetime import datetime, timezone

from webhooks.handlers.github import GitHubWebhookHandler
from webhooks.registry.protocol import WebhookPayload


@pytest.fixture
def handler() -> GitHubWebhookHandler:
    return GitHubWebhookHandler()


@pytest.fixture
def sample_pr_payload() -> dict:
    return {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Fix bug in auth",
            "body": "@agent review this PR",
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main"},
        },
        "repository": {"full_name": "owner/repo"},
        "installation": {"id": 12345},
    }


class TestGitHubWebhookHandlerValidate:
    @pytest.mark.asyncio
    async def test_valid_signature(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        secret = "test_secret"
        payload_bytes = json.dumps(sample_pr_payload).encode()
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        headers = {"x-hub-signature-256": signature}

        result = await handler.validate(payload_bytes, headers, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_signature(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        payload_bytes = json.dumps(sample_pr_payload).encode()
        headers = {"x-hub-signature-256": "sha256=invalid"}

        result = await handler.validate(payload_bytes, headers, "secret")

        assert result is False


class TestGitHubWebhookHandlerParse:
    @pytest.mark.asyncio
    async def test_parse_pr_opened(
        self, handler: GitHubWebhookHandler, sample_pr_payload: dict
    ):
        payload_bytes = json.dumps(sample_pr_payload).encode()
        headers = {"x-github-event": "pull_request"}

        result = await handler.parse(payload_bytes, headers)

        assert result.provider == "github"
        assert result.event_type == "pull_request.opened"
        assert result.installation_id == "12345"
        assert result.metadata["pr_number"] == "42"


class TestGitHubWebhookHandlerShouldProcess:
    @pytest.mark.asyncio
    async def test_should_process_with_agent_mention(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="issue_comment.created",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"comment_body": "@agent review this"},
        )

        result = await handler.should_process(payload)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_not_process_without_mention(
        self, handler: GitHubWebhookHandler
    ):
        payload = WebhookPayload(
            provider="github",
            event_type="issue_comment.created",
            installation_id="12345",
            organization_id="owner",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"comment_body": "Just a regular comment"},
        )

        result = await handler.should_process(payload)

        assert result is False
