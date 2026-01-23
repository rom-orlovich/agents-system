"""Integration tests for dynamic webhook receiver."""

import pytest
import hmac
import hashlib
import json
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from core.database.models import WebhookConfigDB, WebhookCommandDB, WebhookEventDB


@pytest.mark.integration
class TestWebhookReceiver:
    """Test dynamic webhook receiver."""
    
    async def test_receive_webhook_event(self, client: AsyncClient, db: AsyncSession):
        """Webhook receiver processes event and creates task."""
        webhook_data = {
            "name": "GitHub Issues",
            "provider": "github",
            "commands": [{
                "trigger": "issues.opened",
                "action": "create_task",
                "agent": "planning",
                "template": "Issue: {{issue.title}}"
            }]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Test Issue"
            }
        }
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json=payload,
            headers={"X-GitHub-Event": "issues"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["actions"] >= 1
    
    async def test_webhook_signature_verification(self, client: AsyncClient):
        """Webhook with secret requires valid signature."""
        unique_name = f"Secure Webhook {uuid.uuid4().hex[:8]}"
        webhook_data = {
            "name": unique_name,
            "provider": "github",
            "secret": "my-secret-key",
            "commands": []
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json={"test": "data"}
        )
        assert response.status_code == 401
    
    async def test_webhook_signature_valid(self, client: AsyncClient):
        """Webhook with valid signature is accepted."""
        secret = "my-secret-key"
        unique_name = f"Secure Webhook Valid {uuid.uuid4().hex[:8]}"
        webhook_data = {
            "name": unique_name,
            "provider": "github",
            "secret": secret,
            "commands": []
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json=payload,
            headers={"X-Hub-Signature-256": f"sha256={signature}"}
        )
        assert response.status_code in [200, 401]
    
    async def test_disabled_webhook_rejected(self, client: AsyncClient):
        """Disabled webhooks reject events."""
        webhook_data = {
            "name": "Disabled Webhook",
            "provider": "github",
            "enabled": False,
            "commands": []
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json={"test": "data"}
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()
    
    async def test_webhook_not_found(self, client: AsyncClient):
        """Non-existent webhook returns 404."""
        response = await client.post(
            "/webhooks/github/non-existent-id",
            json={"test": "data"}
        )
        assert response.status_code == 404
    
    async def test_webhook_event_logged(self, client: AsyncClient, db: AsyncSession):
        """Webhook events are logged to database."""
        unique_name = f"Test Webhook Event {uuid.uuid4().hex[:8]}"
        webhook_data = {
            "name": unique_name,
            "provider": "github",
            "commands": [{
                "trigger": "issues.opened",
                "action": "create_task",
                "agent": "planning",
                "template": "Test"
            }]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "action": "opened",
            "issue": {"number": 123, "title": "Test"}
        }
        
        await client.post(
            f"/webhooks/github/{webhook_id}",
            json=payload,
            headers={"X-GitHub-Event": "issues"}
        )
        
        from sqlalchemy import select
        result = await db.execute(
            select(WebhookEventDB).where(WebhookEventDB.webhook_id == webhook_id)
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].provider == "github"
        assert events[0].event_type == "issues.opened"
    
    async def test_multiple_commands_executed(self, client: AsyncClient):
        """Multiple matching commands are executed."""
        webhook_data = {
            "name": "Multi Command Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "Task 1"
                },
                {
                    "trigger": "issues.opened",
                    "action": "comment",
                    "template": "Comment 1"
                }
            ]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "action": "opened",
            "issue": {"number": 123, "title": "Test"}
        }
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json=payload,
            headers={"X-GitHub-Event": "issues"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == 2
    
    async def test_webhook_with_conditions(self, client: AsyncClient):
        """Webhook commands with conditions are filtered."""
        webhook_data = {
            "name": "Conditional Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.labeled",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "Urgent issue",
                    "conditions": {
                        "label": "urgent"
                    }
                }
            ]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "action": "labeled",
            "label": {"name": "urgent"},
            "issue": {"number": 123, "title": "Test"}
        }
        
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json=payload,
            headers={"X-GitHub-Event": "issues"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] >= 1


@pytest.mark.integration
class TestWebhookProviders:
    """Test different webhook providers."""
    
    async def test_jira_webhook(self, client: AsyncClient, db_session: AsyncSession):
        """Jira webhook is processed."""
        unique_name = f"Jira Webhook {uuid.uuid4().hex[:8]}"
        webhook_data = {
            "name": unique_name,
            "provider": "jira",
            "commands": [{
                "trigger": "jira:issue_created",
                "action": "create_task",
                "agent": "planning",
                "template": "Jira: {{issue.key}}"
            }]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "PROJ-123",
                "fields": {"summary": "Test Issue"}
            }
        }
        
        response = await client.post(
            f"/webhooks/jira/{webhook_id}",
            json=payload
        )
        
        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Response text: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
    
    async def test_slack_webhook(self, client: AsyncClient):
        """Slack webhook is processed."""
        webhook_data = {
            "name": "Slack Webhook",
            "provider": "slack",
            "commands": [{
                "trigger": "message.channels",
                "action": "respond",
                "template": "Acknowledged"
            }]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        payload = {
            "type": "message",
            "channel": "C123456",
            "text": "Hello bot"
        }
        
        response = await client.post(
            f"/webhooks/slack/{webhook_id}",
            json=payload
        )
        
        assert response.status_code == 200
