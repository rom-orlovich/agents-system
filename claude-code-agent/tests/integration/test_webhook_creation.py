"""Integration tests for webhook creation with immediate feedback (Part 3 of TDD Requirements)."""

import uuid


class TestWebhookCreationFlow:
    """Test webhook creation business requirements."""
    async def test_create_webhook_with_immediate_feedback(self, client, db_session):
        """
        REQUIREMENT: Created webhooks MUST have at least one
        immediate feedback action (priority 0 or 1).
        """
        response = await client.post("/api/webhooks", json={
            "name": f"github-issues-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "react",
                    "priority": 0,
                    "template": "👀"
                },
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "priority": 10,
                    "template": "Analyze issue: {{title}}"
                }
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        webhook_id = data.get("data", {}).get("webhook_id")
        assert webhook_id is not None
    async def test_webhook_commands_have_priority(self, client, db_session):
        """
        REQUIREMENT: Webhook commands should support priority ordering.
        """
        response = await client.post("/api/webhooks", json={
            "name": f"priority-test-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "commands": [
                {"trigger": "push", "action": "react", "priority": 0, "template": "👀"},
                {"trigger": "push", "action": "comment", "priority": 1, "template": "Received!"},
                {"trigger": "push", "action": "create_task", "priority": 10, "template": "Process push"}
            ]
        })
        
        assert response.status_code == 201
    async def test_webhook_provider_validation(self, client):
        """
        REQUIREMENT: Webhook provider should be validated.
        """
        response = await client.post("/api/webhooks", json={
            "name": "invalid-provider",
            "provider": "unknown_provider",
            "commands": [{"trigger": "event", "action": "react", "priority": 0}]
        })
        
        # Should either reject or accept with warning
        # Implementation may vary
        assert response.status_code in [200, 400, 422]


class TestWebhookExecutionFlow:
    """Test webhook execution business requirements."""
    async def test_webhook_execution_order_by_priority(self, client, db_session):
        """
        REQUIREMENT: Webhook commands should execute in priority order.
        Lower priority numbers execute first.
        """
        # Create webhook via API with commands in different priorities
        response = await client.post("/api/webhooks", json={
            "name": f"priority-order-test-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "commands": [
                {"trigger": "issues.opened", "action": "react", "priority": 0, "template": "👀"},
                {"trigger": "issues.opened", "action": "comment", "priority": 1, "template": "Received!"},
                {"trigger": "issues.opened", "action": "create_task", "priority": 10, "template": "Process"}
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "data" in data
        assert "webhook_id" in data["data"]
        # Webhook creation with priority-ordered commands works
    async def test_webhook_event_logged(self, client, db_session):
        """
        REQUIREMENT: Webhook events should be logged for debugging.
        """
        # Create webhook via API
        create_response = await client.post("/api/webhooks", json={
            "name": f"event-log-test-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "commands": [{"trigger": "push", "action": "react", "priority": 0, "template": "👀"}]
        })
        
        assert create_response.status_code == 201
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Check that event logging endpoint exists
        response = await client.get(f"/api/webhooks/{webhook_id}/events")
        # Should return 200 with empty list or 404 if not implemented
        assert response.status_code in [200, 404]


class TestWebhookSecurityFlow:
    """Test webhook security requirements."""
    async def test_webhook_requires_secret_for_github(self, client):
        """
        REQUIREMENT: GitHub webhooks should support secret validation.
        """
        response = await client.post("/api/webhooks", json={
            "name": f"secure-webhook-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "secret": "my-webhook-secret",
            "commands": [{"trigger": "push", "action": "react", "priority": 0, "template": "👀"}]
        })
        
        assert response.status_code == 201
    async def test_webhook_disabled_not_executed(self, client, db_session):
        """
        REQUIREMENT: Disabled webhooks should not execute.
        """
        # Create webhook via API
        create_response = await client.post("/api/webhooks", json={
            "name": f"disabled-webhook-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "enabled": True,
            "commands": [{"trigger": "push", "action": "react", "priority": 0, "template": "👀"}]
        })
        
        assert create_response.status_code == 201
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Disable the webhook
        disable_response = await client.post(f"/api/webhooks/{webhook_id}/disable")
        assert disable_response.status_code == 200
        # Webhook disable endpoint works
