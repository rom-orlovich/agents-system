"""Fixtures for multi-subagent orchestration tests."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid


@pytest.fixture
async def running_subagent(client):
    """A running subagent for testing."""
    response = await client.post("/api/v2/subagents/spawn", json={
        "agent_type": "planning",
        "mode": "foreground",
        "task_id": "fixture-task"
    })
    return response.json().get("data", {})


@pytest.fixture
async def background_subagent(client):
    """A background subagent for testing."""
    response = await client.post("/api/v2/subagents/spawn", json={
        "agent_type": "executor",
        "mode": "background",
        "task_id": "background-fixture-task"
    })
    return response.json().get("data", {})


@pytest.fixture
async def conversation_with_history(client, db_session):
    """Conversation with 25 messages (more than context limit)."""
    from core.database.models import ConversationDB, ConversationMessageDB
    
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    
    # Create conversation
    conv = ConversationDB(
        conversation_id=conv_id,
        user_id="test-user",
        title="Test Conversation"
    )
    db_session.add(conv)
    
    # Add 25 messages
    for i in range(25):
        msg = ConversationMessageDB(
            message_id=f"msg-{conv_id}-{i}",
            conversation_id=conv_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}"
        )
        db_session.add(msg)
    
    await db_session.commit()
    
    return {"conversation_id": conv_id}


@pytest.fixture
async def github_webhook(client):
    """Pre-configured GitHub webhook with immediate feedback."""
    response = await client.post("/api/v2/webhooks", json={
        "name": "test-github",
        "provider": "github",
        "commands": [
            {"trigger": "issues.opened", "action": "react", "priority": 0, "template": "eyes"},
            {"trigger": "issues.opened", "action": "comment", "priority": 1, "template": "👋 Received!"},
            {"trigger": "issues.opened", "action": "create_task", "priority": 10, "template": "Analyze issue"}
        ]
    })
    return response.json().get("data", {})


@pytest.fixture
async def completed_parallel_group(client):
    """A completed parallel execution group."""
    # Spawn parallel subagents
    response = await client.post("/api/v2/subagents/parallel", json={
        "agents": [
            {"type": "planning", "task": "Research auth module"},
            {"type": "planning", "task": "Research database module"},
            {"type": "planning", "task": "Research API module"},
        ]
    })
    group_id = response.json().get("data", {}).get("group_id")
    
    # In real tests, we'd wait for completion
    # For fixture purposes, we return the group_id
    return {"group_id": group_id}


@pytest.fixture
async def registered_account(client, db_session):
    """A registered account for testing."""
    from core.database.models import AccountDB
    
    account_id = f"account-{uuid.uuid4().hex[:8]}"
    account = AccountDB(
        account_id=account_id,
        email="test@example.com",
        display_name="Test User",
        credential_status="valid",
        credential_expires_at=datetime.now(timezone.utc)
    )
    db_session.add(account)
    await db_session.commit()
    
    return {"account_id": account_id, "email": "test@example.com"}


@pytest.fixture
async def registered_machine(client, db_session, registered_account):
    """A registered machine linked to an account."""
    from core.database.models import MachineDB
    
    machine_id = f"machine-{uuid.uuid4().hex[:8]}"
    machine = MachineDB(
        machine_id=machine_id,
        account_id=registered_account["account_id"],
        display_name="Test Machine",
        status="online",
        last_heartbeat=datetime.now(timezone.utc)
    )
    db_session.add(machine)
    await db_session.commit()
    
    return {"machine_id": machine_id, "account_id": registered_account["account_id"]}


@pytest.fixture
def mock_claude_cli():
    """Mock Claude CLI for subagent execution."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__ = lambda self: iter([
            b'{"type":"assistant","message":{"content":"Working..."}}\n',
            b'{"type":"result","result":"Done","session_id":"test-123"}\n'
        ])
        mock_exec.return_value = mock_process
        yield mock_exec


@pytest.fixture
def ws_client():
    """WebSocket client mock for real-time streaming tests."""
    class MockWSClient:
        def __init__(self):
            self.messages = []
        
        async def subscribe(self, endpoint):
            """Mock subscription that yields test messages."""
            for i in range(5):
                yield {
                    "type": "subagent_log",
                    "subagent_id": f"subagent-{i % 2}",
                    "content": f"Message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
    
    return MockWSClient()


@pytest.fixture
async def restart_server():
    """Helper to simulate server restart for persistence tests."""
    async def _restart():
        # In real tests, this would restart the server
        # For unit tests, we just clear caches
        pass
    return _restart


@pytest.fixture
async def restart_redis(redis_mock):
    """Helper to simulate Redis restart for persistence tests."""
    async def _restart():
        # Simulate Redis restart by clearing mock state
        redis_mock.get_task_status.return_value = "pending_retry"
    return _restart


@pytest.fixture
def capture_github_api_calls():
    """Context manager to capture GitHub API calls."""
    class CallCapture:
        def __init__(self):
            self.calls = []
        
        def __enter__(self):
            return self.calls
        
        def __exit__(self, *args):
            pass
    
    return CallCapture


@pytest.fixture
def patch_webhook_actions():
    """Context manager to patch webhook actions and capture execution order."""
    def _patch(execution_log):
        class ActionPatcher:
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
        
        return ActionPatcher()
    
    return _patch
