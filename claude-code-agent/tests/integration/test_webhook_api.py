"""Integration tests for webhook management API endpoints."""

import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import WebhookConfigDB, WebhookCommandDB


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebhookAPI:
    """Test webhook management API endpoints."""
    
    async def test_list_webhooks_empty(self, client: AsyncClient):
        """List webhooks returns empty array when none exist."""
        response = await client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    async def test_create_webhook(self, client: AsyncClient):
        """Create a new webhook configuration."""
        webhook_data = {
            "name": "Test GitHub Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "New issue: {{issue.title}}"
                }
            ]
        }
        
        response = await client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "webhook_id" in data["data"]
        assert "endpoint" in data["data"]
        assert data["data"]["name"] == "Test GitHub Webhook"
        assert data["data"]["provider"] == "github"
    
    async def test_create_webhook_with_secret(self, client: AsyncClient):
        """Create webhook with secret for signature verification."""
        webhook_data = {
            "name": "Secure Webhook",
            "provider": "github",
            "secret": "my-secret-key",
            "commands": []
        }
        
        response = await client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 201
        data = response.json()
        assert "webhook_id" in data["data"]
    
    async def test_create_webhook_duplicate_name(self, client: AsyncClient):
        """Creating webhook with duplicate name is rejected."""
        webhook_data = {"name": "Duplicate", "provider": "github", "commands": []}
        
        await client.post("/api/webhooks", json=webhook_data)
        
        response = await client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    async def test_create_webhook_invalid_provider(self, client: AsyncClient):
        """Creating webhook with invalid provider is rejected."""
        webhook_data = {
            "name": "Invalid Provider",
            "provider": "invalid-provider",
            "commands": []
        }
        
        response = await client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 400
    
    async def test_get_webhook(self, client: AsyncClient):
        """Get webhook details by ID."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.get(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["webhook_id"] == webhook_id
        assert data["name"] == "Test Webhook"
        assert data["provider"] == "github"
        assert data["enabled"] is True
        assert isinstance(data["commands"], list)
    
    async def test_get_webhook_not_found(self, client: AsyncClient):
        """Get non-existent webhook returns 404."""
        response = await client.get("/api/webhooks/non-existent-id")
        assert response.status_code == 404
    
    async def test_list_webhooks(self, client: AsyncClient):
        """List all webhooks."""
        await client.post("/api/webhooks", json={
            "name": "Webhook 1",
            "provider": "github",
            "commands": []
        })
        await client.post("/api/webhooks", json={
            "name": "Webhook 2",
            "provider": "jira",
            "commands": []
        })
        
        response = await client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [w["name"] for w in data]
        assert "Webhook 1" in names
        assert "Webhook 2" in names
    
    async def test_update_webhook(self, client: AsyncClient):
        """Update webhook configuration."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Original Name",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.put(f"/api/webhooks/{webhook_id}", json={
            "name": "Updated Name",
            "enabled": False
        })
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        data = get_response.json()
        assert data["name"] == "Updated Name"
        assert data["enabled"] is False
    
    async def test_update_webhook_not_found(self, client: AsyncClient):
        """Update non-existent webhook returns 404."""
        response = await client.put("/api/webhooks/non-existent", json={
            "name": "Updated"
        })
        assert response.status_code == 404
    
    async def test_delete_webhook(self, client: AsyncClient):
        """Delete webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "To Delete",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.delete(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 404
    
    async def test_delete_webhook_not_found(self, client: AsyncClient):
        """Delete non-existent webhook returns 404."""
        response = await client.delete("/api/webhooks/non-existent")
        assert response.status_code == 404
    
    async def test_enable_webhook(self, client: AsyncClient):
        """Enable a disabled webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "enabled": False,
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(f"/api/webhooks/{webhook_id}/enable")
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.json()["enabled"] is True
    
    async def test_disable_webhook(self, client: AsyncClient):
        """Disable an enabled webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(f"/api/webhooks/{webhook_id}/disable")
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.json()["enabled"] is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebhookCommandAPI:
    """Test webhook command management API endpoints."""
    
    async def test_add_command_to_webhook(self, client: AsyncClient):
        """Add command to existing webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        command_data = {
            "trigger": "pull_request.opened",
            "action": "create_task",
            "agent": "executor",
            "template": "New PR: {{pr.title}}"
        }
        response = await client.post(
            f"/api/webhooks/{webhook_id}/commands",
            json=command_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "command_id" in data["data"]
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        webhook_data = get_response.json()
        assert len(webhook_data["commands"]) == 1
        assert webhook_data["commands"][0]["trigger"] == "pull_request.opened"
    
    async def test_add_command_with_conditions(self, client: AsyncClient):
        """Add command with trigger conditions."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        command_data = {
            "trigger": "issues.labeled",
            "action": "create_task",
            "agent": "planning",
            "template": "Urgent issue: {{issue.title}}",
            "conditions": {
                "label": "urgent"
            }
        }
        response = await client.post(
            f"/api/webhooks/{webhook_id}/commands",
            json=command_data
        )
        assert response.status_code == 201
    
    async def test_list_commands(self, client: AsyncClient):
        """List all commands for a webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "Issue: {{issue.title}}"
                },
                {
                    "trigger": "pull_request.opened",
                    "action": "create_task",
                    "agent": "executor",
                    "template": "PR: {{pr.title}}"
                }
            ]
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.get(f"/api/webhooks/{webhook_id}/commands")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    async def test_update_command(self, client: AsyncClient):
        """Update existing command."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "Original template"
                }
            ]
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        command_id = get_response.json()["commands"][0]["command_id"]
        
        response = await client.put(
            f"/api/webhooks/{webhook_id}/commands/{command_id}",
            json={
                "template": "Updated template",
                "action": "ask"
            }
        )
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        updated_command = get_response.json()["commands"][0]
        assert updated_command["template"] == "Updated template"
        assert updated_command["action"] == "ask"
    
    async def test_delete_command(self, client: AsyncClient):
        """Delete command from webhook."""
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "agent": "planning",
                    "template": "Test"
                }
            ]
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        command_id = get_response.json()["commands"][0]["command_id"]
        
        response = await client.delete(
            f"/api/webhooks/{webhook_id}/commands/{command_id}"
        )
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert len(get_response.json()["commands"]) == 0
    
    async def test_add_command_to_nonexistent_webhook(self, client: AsyncClient):
        """Adding command to non-existent webhook returns 404."""
        response = await client.post(
            "/api/webhooks/non-existent/commands",
            json={
                "trigger": "test",
                "action": "create_task",
                "agent": "planning",
                "template": "test"
            }
        )
        assert response.status_code == 404
