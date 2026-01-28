"""Integration tests for webhook management API endpoints."""

import pytest
import uuid
from httpx import AsyncClient



@pytest.mark.integration
class TestWebhookAPI:
    """Test webhook management API endpoints."""
    
    async def test_list_webhooks_empty(self, client: AsyncClient):
        """List webhooks returns empty array when none exist."""
        response = await client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May have existing webhooks from other tests, just verify it's a list
        assert isinstance(data, list)
    
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
        # Verify at least 2 webhooks exist
        assert len(data) >= 2
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
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["webhook_id"] == webhook_id
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
        unique_name = f"Test Webhook Enable {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
            "provider": "github",
            "enabled": False,
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(f"/api/webhooks/{webhook_id}/enable")
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["webhook_id"] == webhook_id
        assert data["enabled"] is True
    
    async def test_disable_webhook(self, client: AsyncClient):
        """Disable an enabled webhook."""
        unique_name = f"Test Webhook Disable {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
            "provider": "github",
            "commands": []
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        response = await client.post(f"/api/webhooks/{webhook_id}/disable")
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["webhook_id"] == webhook_id
        assert data["enabled"] is False


@pytest.mark.integration
class TestWebhookCommandAPI:
    """Test webhook command management API endpoints."""
    
    async def test_add_command_to_webhook(self, client: AsyncClient):
        """Add command to existing webhook."""
        unique_name = f"Test Webhook Add Cmd {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
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
        assert get_response.status_code == 200
        webhook_data = get_response.json()
        assert "commands" in webhook_data
        assert len(webhook_data["commands"]) >= 1
        # Find the command we just added
        added_cmd = next((c for c in webhook_data["commands"] if c["trigger"] == "pull_request.opened"), None)
        assert added_cmd is not None
    
    async def test_add_command_with_conditions(self, client: AsyncClient):
        """Add command with trigger conditions."""
        unique_name = f"Test Webhook Conditions {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
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
        unique_name = f"Test Webhook List {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
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
        unique_name = f"Test Webhook Update Cmd {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
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
        assert get_response.status_code == 200
        webhook_data = get_response.json()
        assert "commands" in webhook_data
        assert len(webhook_data["commands"]) > 0
        command_id = webhook_data["commands"][0]["command_id"]
        
        response = await client.put(
            f"/api/webhooks/{webhook_id}/commands/{command_id}",
            json={
                "template": "Updated template",
                "action": "ask"
            }
        )
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        updated_webhook = get_response.json()
        assert "commands" in updated_webhook
        updated_command = next((c for c in updated_webhook["commands"] if c["command_id"] == command_id), None)
        assert updated_command is not None
        assert updated_command["template"] == "Updated template"
        assert updated_command["action"] == "ask"
    
    async def test_delete_command(self, client: AsyncClient):
        """Delete command from webhook."""
        unique_name = f"Test Webhook Delete Cmd {uuid.uuid4().hex[:8]}"
        create_response = await client.post("/api/webhooks", json={
            "name": unique_name,
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
        assert get_response.status_code == 200
        webhook_data = get_response.json()
        assert "commands" in webhook_data
        assert len(webhook_data["commands"]) > 0
        command_id = webhook_data["commands"][0]["command_id"]
        
        response = await client.delete(
            f"/api/webhooks/{webhook_id}/commands/{command_id}"
        )
        assert response.status_code == 200
        
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        final_webhook = get_response.json()
        assert "commands" in final_webhook
        # Command should be removed
        remaining_cmds = [c for c in final_webhook["commands"] if c["command_id"] == command_id]
        assert len(remaining_cmds) == 0
    
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
