# Test-Driven Development (TDD) Approach

## Overview

All new features MUST follow TDD methodology:
1. **Write tests first** - Before any implementation
2. **Run tests** - Verify they fail (red)
3. **Implement** - Write minimal code to pass tests
4. **Run tests** - Verify they pass (green)
5. **Refactor** - Improve code while keeping tests green

---

## TDD for Webhook System

### **Phase 1: Database Models Tests**

```python
# tests/unit/test_webhook_models.py

import pytest
from datetime import datetime
from core.database.models import WebhookConfigDB, WebhookCommandDB, WebhookEventDB

class TestWebhookConfigDB:
    """Test webhook configuration model."""
    
    def test_create_webhook_config(self):
        """Test creating a webhook configuration."""
        webhook = WebhookConfigDB(
            webhook_id="test-webhook-001",
            name="Test Webhook",
            provider="github",
            endpoint="/webhooks/github/test-webhook-001",
            enabled=True,
            config_json='{"test": true}',
            created_by="user-123"
        )
        assert webhook.webhook_id == "test-webhook-001"
        assert webhook.enabled is True
    
    def test_webhook_relationships(self):
        """Test webhook has commands and events relationships."""
        webhook = WebhookConfigDB(webhook_id="test-001", ...)
        assert hasattr(webhook, 'commands')
        assert hasattr(webhook, 'events')

class TestWebhookCommandDB:
    """Test webhook command model."""
    
    def test_create_command(self):
        """Test creating a webhook command."""
        command = WebhookCommandDB(
            command_id="cmd-001",
            webhook_id="webhook-001",
            trigger="issues.opened",
            action="create_task",
            agent="planning",
            template="New issue: {{issue.title}}",
            priority=0
        )
        assert command.action == "create_task"
        assert command.agent == "planning"
    
    def test_command_belongs_to_webhook(self):
        """Test command has webhook relationship."""
        command = WebhookCommandDB(command_id="cmd-001", ...)
        assert hasattr(command, 'webhook')

class TestWebhookEventDB:
    """Test webhook event log model."""
    
    def test_create_event(self):
        """Test creating a webhook event."""
        event = WebhookEventDB(
            event_id="evt-001",
            webhook_id="webhook-001",
            provider="github",
            event_type="issues.opened",
            payload_json='{"issue": {"number": 123}}',
            matched_command="cmd-001",
            task_id="task-001",
            response_sent=True
        )
        assert event.event_type == "issues.opened"
        assert event.response_sent is True
```

### **Phase 2: Webhook CRUD API Tests**

```python
# tests/integration/test_webhook_api.py

import pytest
from httpx import AsyncClient

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
    
    async def test_create_webhook_duplicate_name(self, client: AsyncClient):
        """Creating webhook with duplicate name is rejected."""
        webhook_data = {"name": "Duplicate", "provider": "github"}
        
        # Create first webhook
        await client.post("/api/webhooks", json=webhook_data)
        
        # Try to create duplicate
        response = await client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    async def test_get_webhook(self, client: AsyncClient):
        """Get webhook details by ID."""
        # Create webhook first
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github"
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Get webhook
        response = await client.get(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["webhook_id"] == webhook_id
        assert data["name"] == "Test Webhook"
    
    async def test_update_webhook(self, client: AsyncClient):
        """Update webhook configuration."""
        # Create webhook
        create_response = await client.post("/api/webhooks", json={
            "name": "Original Name",
            "provider": "github"
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Update webhook
        response = await client.put(f"/api/webhooks/{webhook_id}", json={
            "name": "Updated Name",
            "enabled": False
        })
        assert response.status_code == 200
        
        # Verify update
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        data = get_response.json()
        assert data["name"] == "Updated Name"
        assert data["enabled"] is False
    
    async def test_delete_webhook(self, client: AsyncClient):
        """Delete webhook."""
        # Create webhook
        create_response = await client.post("/api/webhooks", json={
            "name": "To Delete",
            "provider": "github"
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Delete webhook
        response = await client.delete(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
        
        # Verify deletion
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        assert get_response.status_code == 404
    
    async def test_add_command_to_webhook(self, client: AsyncClient):
        """Add command to existing webhook."""
        # Create webhook
        create_response = await client.post("/api/webhooks", json={
            "name": "Test Webhook",
            "provider": "github"
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Add command
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
        
        # Verify command added
        get_response = await client.get(f"/api/webhooks/{webhook_id}")
        data = get_response.json()
        assert len(data["commands"]) == 1
        assert data["commands"][0]["trigger"] == "pull_request.opened"
```

### **Phase 3: Dynamic Webhook Receiver Tests**

```python
# tests/integration/test_webhook_receiver.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestWebhookReceiver:
    """Test dynamic webhook receiver."""
    
    async def test_receive_webhook_event(self, client: AsyncClient, db: AsyncSession):
        """Webhook receiver processes event and creates task."""
        # Create webhook with command
        webhook_data = {
            "name": "GitHub Issues",
            "provider": "github",
            "secret": "test-secret",
            "commands": [{
                "trigger": "issues.opened",
                "action": "create_task",
                "agent": "planning",
                "template": "Issue: {{issue.title}}"
            }]
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Send webhook event
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
        assert "task_id" in data
    
    async def test_webhook_signature_verification(self, client: AsyncClient):
        """Webhook with secret requires valid signature."""
        # Create webhook with secret
        webhook_data = {
            "name": "Secure Webhook",
            "provider": "github",
            "secret": "my-secret-key"
        }
        create_response = await client.post("/api/webhooks", json=webhook_data)
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Send without signature
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json={"test": "data"}
        )
        assert response.status_code == 401
    
    async def test_disabled_webhook_rejected(self, client: AsyncClient):
        """Disabled webhooks reject events."""
        # Create and disable webhook
        create_response = await client.post("/api/webhooks", json={
            "name": "Disabled Webhook",
            "provider": "github",
            "enabled": False
        })
        webhook_id = create_response.json()["data"]["webhook_id"]
        
        # Try to send event
        response = await client.post(
            f"/webhooks/github/{webhook_id}",
            json={"test": "data"}
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()
```

### **Phase 4: Command Execution Tests**

```python
# tests/unit/test_webhook_engine.py

@pytest.mark.asyncio
class TestWebhookEngine:
    """Test webhook command execution engine."""
    
    async def test_execute_create_task_command(self, db: AsyncSession):
        """Execute create_task command creates a task."""
        command = WebhookCommandDB(
            command_id="cmd-001",
            trigger="issues.opened",
            action="create_task",
            agent="planning",
            template="Issue: {{issue.title}}"
        )
        
        payload = {"issue": {"title": "Test Issue"}}
        
        result = await execute_command(command, payload, db)
        
        assert result["action"] == "create_task"
        assert "task_id" in result
    
    async def test_execute_comment_command(self):
        """Execute comment command posts comment."""
        command = WebhookCommandDB(
            action="comment",
            template="Acknowledged: {{issue.number}}"
        )
        
        payload = {"issue": {"number": 123}, "provider": "github"}
        
        result = await execute_command(command, payload, None)
        
        assert result["action"] == "comment"
        assert result["status"] == "sent"
    
    async def test_template_rendering(self):
        """Template rendering replaces variables."""
        template = "Issue #{{issue.number}}: {{issue.title}}"
        payload = {"issue": {"number": 123, "title": "Bug Report"}}
        
        rendered = render_template(template, payload)
        
        assert rendered == "Issue #123: Bug Report"
```

---

## TDD for Account Management

### **Account Info Display Tests**

```python
# tests/integration/test_account_info.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestAccountInfo:
    """Test account information display."""
    
    async def test_credential_status_includes_account_info(self, client: AsyncClient, tmp_path):
        """Credential status returns account email and ID."""
        # Create valid credentials file
        creds_path = tmp_path / "claude.json"
        creds_data = {
            "email": "test@example.com",
            "user_id": "user-123",
            "session_key": "key-123",
            "expires_at": int((datetime.utcnow() + timedelta(hours=2)).timestamp() * 1000)
        }
        creds_path.write_text(json.dumps(creds_data))
        
        with patch("core.config.settings.credentials_path", creds_path):
            response = await client.get("/api/credentials/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_email"] == "test@example.com"
        assert data["account_id"] == "user-123"
    
    async def test_list_all_accounts(self, client: AsyncClient, db: AsyncSession):
        """List all accounts from database."""
        # Create test sessions with different users
        session1 = SessionDB(
            session_id="sess-1",
            user_id="user-1",
            machine_id="machine-1"
        )
        session2 = SessionDB(
            session_id="sess-2",
            user_id="user-2",
            machine_id="machine-1"
        )
        db.add_all([session1, session2])
        await db.commit()
        
        response = await client.get("/api/accounts")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["accounts"]) == 2
        user_ids = [acc["user_id"] for acc in data["accounts"]]
        assert "user-1" in user_ids
        assert "user-2" in user_ids
```

---

## Test Execution Order

### **1. Run Unit Tests First**
```bash
pytest tests/unit/ -v
```

### **2. Run Integration Tests**
```bash
pytest tests/integration/ -v
```

### **3. Run E2E Tests**
```bash
pytest tests/e2e/ -v
```

### **4. Check Coverage**
```bash
pytest --cov=api --cov=core --cov-report=html
```

**Minimum coverage requirement: 80%**

---

## TDD Workflow Example

### **Feature: Webhook Registration**

**Step 1: Write Test (RED)**
```python
async def test_create_webhook(client):
    response = await client.post("/api/webhooks", json={
        "name": "Test Webhook",
        "provider": "github"
    })
    assert response.status_code == 201
```

**Step 2: Run Test - FAILS** ✗
```
FAILED - 404 Not Found
```

**Step 3: Implement Minimal Code (GREEN)**
```python
@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate):
    return {"success": True}, 201
```

**Step 4: Run Test - PASSES** ✓
```
PASSED
```

**Step 5: Refactor**
```python
@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate, db: AsyncSession):
    webhook_id = f"webhook-{uuid.uuid4().hex[:12]}"
    webhook_db = WebhookConfigDB(
        webhook_id=webhook_id,
        name=webhook.name,
        provider=webhook.provider,
        ...
    )
    db.add(webhook_db)
    await db.commit()
    return {"success": True, "data": {"webhook_id": webhook_id}}, 201
```

**Step 6: Run Test - STILL PASSES** ✓

---

## Continuous Integration

### **GitHub Actions Workflow**

```yaml
name: TDD Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ -v
      - name: Run integration tests
        run: pytest tests/integration/ -v
      - name: Check coverage
        run: pytest --cov=api --cov=core --cov-report=term-missing
```

---

## Summary

**TDD ensures:**
- ✅ All features have tests before implementation
- ✅ Code is testable by design
- ✅ Regression prevention
- ✅ Documentation through tests
- ✅ Confidence in refactoring
- ✅ Faster debugging

**No code ships without tests!**
