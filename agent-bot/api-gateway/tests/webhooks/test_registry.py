import pytest
from datetime import datetime, timezone

from webhooks.registry.protocol import (
    WebhookPayload,
    WebhookResponse,
    TaskCreationRequest,
)
from webhooks.registry.registry import WebhookRegistry


class MockWebhookHandler:
    def __init__(self, provider: str):
        self._provider = provider

    async def validate(self, payload: bytes, headers: dict, secret: str) -> bool:
        return True

    async def parse(self, payload: bytes, headers: dict) -> WebhookPayload:
        return WebhookPayload(
            provider=self._provider,
            event_type="test_event",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={"test": "data"},
            timestamp=datetime.now(timezone.utc),
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        return True

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        return TaskCreationRequest(
            provider=self._provider,
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message="Test message",
            source_metadata={},
            priority=2,
        )


class TestWebhookRegistry:
    @pytest.fixture
    def registry(self) -> WebhookRegistry:
        return WebhookRegistry()

    def test_register_handler(self, registry: WebhookRegistry):
        handler = MockWebhookHandler("github")
        registry.register("github", handler)

        assert "github" in registry.list_providers()

    def test_get_registered_handler(self, registry: WebhookRegistry):
        handler = MockWebhookHandler("github")
        registry.register("github", handler)

        retrieved = registry.get_handler("github")

        assert retrieved is handler

    def test_get_unregistered_handler_returns_none(
        self, registry: WebhookRegistry
    ):
        result = registry.get_handler("unknown")

        assert result is None

    def test_list_providers(self, registry: WebhookRegistry):
        registry.register("github", MockWebhookHandler("github"))
        registry.register("jira", MockWebhookHandler("jira"))

        providers = registry.list_providers()

        assert set(providers) == {"github", "jira"}


class TestWebhookPayload:
    def test_create_valid_payload(self):
        payload = WebhookPayload(
            provider="github",
            event_type="pull_request.opened",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={"action": "opened"},
            timestamp=datetime.now(timezone.utc),
        )

        assert payload.provider == "github"
        assert payload.event_type == "pull_request.opened"

    def test_payload_with_metadata(self):
        payload = WebhookPayload(
            provider="github",
            event_type="pull_request.opened",
            installation_id="inst-123",
            organization_id="org-456",
            raw_payload={},
            timestamp=datetime.now(timezone.utc),
            metadata={"pr_number": "42", "repo": "owner/repo"},
        )

        assert payload.metadata["pr_number"] == "42"
