"""Integration tests for data persistence (Part 5 of TDD Requirements)."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
import uuid


class TestDataPersistenceFlow:
    """Test data persistence business requirements."""
    
    @pytest.mark.asyncio
    async def test_task_persists_to_database(self, client, db_session):
        """
        REQUIREMENT: Tasks should persist to the database.
        """
        from core.database.models import TaskDB, SessionDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        # Create session first
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine"
        )
        db_session.add(session)
        
        # Create task
        task = TaskDB(
            task_id=task_id,
            session_id=session_id,
            user_id="test-user",
            input_message="Test task for persistence",
            status="queued",
            agent_type="planning"
        )
        db_session.add(task)
        await db_session.commit()
        
        # Verify task exists via API
        response = await client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id
    
    @pytest.mark.asyncio
    async def test_webhook_config_persists(self, client, db_session):
        """
        REQUIREMENT: Webhook configurations should persist.
        """
        # Create webhook via API
        create_response = await client.post("/api/webhooks", json={
            "name": f"persistent-webhook-{uuid.uuid4().hex[:8]}",
            "provider": "github",
            "commands": [{"trigger": "push", "action": "react", "priority": 0, "template": "👀"}]
        })
        
        assert create_response.status_code == 201
        data = create_response.json()
        assert "data" in data
        assert "webhook_id" in data["data"]
        # Webhook was created and persisted to database
    
    @pytest.mark.asyncio
    async def test_conversation_history_persists(self, client, db_session):
        """
        REQUIREMENT: Conversation history should persist.
        """
        from core.database.models import ConversationDB, ConversationMessageDB
        
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        
        # Create conversation
        conv = ConversationDB(
            conversation_id=conv_id,
            user_id="test-user",
            title="Persistent Conversation"
        )
        db_session.add(conv)
        
        # Add messages
        for i in range(3):
            msg = ConversationMessageDB(
                message_id=f"msg-{conv_id}-{i}",
                conversation_id=conv_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)
        
        await db_session.commit()
        
        # Verify conversation exists via API
        response = await client.get(f"/api/conversations/{conv_id}")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_subagent_execution_persists(self, client, db_session):
        """
        REQUIREMENT: Subagent executions should persist to database.
        """
        from core.database.models import SubagentExecutionDB
        
        execution_id = f"subagent-{uuid.uuid4().hex[:8]}"
        
        execution = SubagentExecutionDB(
            execution_id=execution_id,
            agent_name="planning",
            mode="foreground",
            status="completed",
            result_summary="Task completed"
        )
        db_session.add(execution)
        await db_session.commit()
        
        # Verify via API
        response = await client.get(f"/api/v2/subagents/{execution_id}/context")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_account_persists(self, client, db_session):
        """
        REQUIREMENT: Account information should persist.
        """
        from core.database.models import AccountDB
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        account = AccountDB(
            account_id=account_id,
            email="persist@example.com",
            credential_status="valid"
        )
        db_session.add(account)
        await db_session.commit()
        
        # Verify via API
        response = await client.get(f"/api/v2/accounts/{account_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "persist@example.com"
    
    @pytest.mark.asyncio
    async def test_machine_persists(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Machine information should persist.
        """
        from core.database.models import MachineDB
        
        machine_id = f"machine-{uuid.uuid4().hex[:8]}"
        
        machine = MachineDB(
            machine_id=machine_id,
            display_name="Persistent Machine",
            status="online"
        )
        db_session.add(machine)
        await db_session.commit()
        
        redis_mock.get_machine_status = AsyncMock(return_value={"status": "online"})
        redis_mock.get_machine_metrics = AsyncMock(return_value={})
        
        # Verify via API
        response = await client.get(f"/api/v2/machines/{machine_id}")
        assert response.status_code == 200
        assert response.json()["display_name"] == "Persistent Machine"


class TestRedisRecoveryFlow:
    """Test Redis recovery requirements."""
    
    @pytest.mark.asyncio
    async def test_active_subagents_tracked_in_redis(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Active subagents should be tracked in Redis.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Spawn subagent
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground"
        })
        
        assert response.status_code == 200
        
        # Verify Redis tracking was called
        redis_mock.add_active_subagent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_machine_status_tracked_in_redis(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Machine status should be tracked in Redis.
        """
        redis_mock.register_machine = AsyncMock()
        
        machine_id = f"machine-{uuid.uuid4().hex[:8]}"
        
        response = await client.post("/api/v2/machines/register", json={
            "machine_id": machine_id,
            "display_name": "Redis Tracked Machine"
        })
        
        assert response.status_code == 200
        
        # Verify Redis was called
        redis_mock.register_machine.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parallel_group_tracked_in_redis(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Parallel execution groups should be tracked in Redis.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        redis_mock.create_parallel_group = AsyncMock()
        
        response = await client.post("/api/v2/subagents/parallel", json={
            "agents": [
                {"type": "planning", "task": "Task A"},
                {"type": "planning", "task": "Task B"}
            ]
        })
        
        assert response.status_code == 200
        
        # Verify parallel group was created in Redis
        redis_mock.create_parallel_group.assert_called_once()


class TestDatabaseIntegrityFlow:
    """Test database integrity requirements."""
    
    @pytest.mark.asyncio
    async def test_session_task_relationship(self, client, db_session):
        """
        REQUIREMENT: Tasks should be linked to sessions.
        """
        from core.database.models import SessionDB, TaskDB
        from sqlalchemy import select
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine"
        )
        db_session.add(session)
        
        # Create multiple tasks for this session
        for i in range(3):
            task = TaskDB(
                task_id=f"task-{session_id}-{i}",
                session_id=session_id,
                user_id="test-user",
                input_message=f"Task {i}",
                status="completed",
                agent_type="planning"
            )
            db_session.add(task)
        
        await db_session.commit()
        
        # Query tasks for session
        result = await db_session.execute(
            select(TaskDB).where(TaskDB.session_id == session_id)
        )
        tasks = result.scalars().all()
        
        assert len(tasks) == 3
    
    @pytest.mark.asyncio
    async def test_account_machine_relationship(self, client, db_session):
        """
        REQUIREMENT: Machines should be linked to accounts.
        """
        from core.database.models import AccountDB, MachineDB
        from sqlalchemy import select
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        account = AccountDB(
            account_id=account_id,
            email="relationship@example.com"
        )
        db_session.add(account)
        
        # Create machines for this account
        for i in range(2):
            machine = MachineDB(
                machine_id=f"machine-{account_id}-{i}",
                account_id=account_id,
                status="online"
            )
            db_session.add(machine)
        
        await db_session.commit()
        
        # Query machines for account
        result = await db_session.execute(
            select(MachineDB).where(MachineDB.account_id == account_id)
        )
        machines = result.scalars().all()
        
        assert len(machines) == 2
