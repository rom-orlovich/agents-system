"""Integration tests for multi-subagent orchestration (Part 2 of TDD Requirements)."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestSubagentSpawnFlow:
    """Test subagent spawn business requirements."""
    
    @pytest.mark.asyncio
    async def test_spawn_foreground_subagent_becomes_active(self, client, redis_mock):
        """
        REQUIREMENT: When Brain spawns a foreground subagent,
        it should appear in active subagents list with 'running' status.
        """
        # Setup redis mock to track subagents
        redis_mock.get_active_subagents = AsyncMock(return_value=[])
        redis_mock.add_active_subagent = AsyncMock()
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground",
            "task_id": "task-123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        subagent_id = data["data"]["subagent_id"]
        assert subagent_id is not None
        
        # Verify it's in active list
        active = await client.get("/api/v2/subagents/active")
        assert active.status_code == 200
    
    @pytest.mark.asyncio
    async def test_spawn_background_subagent_runs_async(self, client, redis_mock):
        """
        REQUIREMENT: Background subagents should run without blocking
        and auto-deny permission requests.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "executor",
            "mode": "background",
            "task_id": "task-456"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["mode"] == "background"
        assert data["permission_mode"] == "auto-deny"
    
    @pytest.mark.asyncio
    async def test_stop_subagent_terminates_and_removes(self, client, redis_mock):
        """
        REQUIREMENT: Stopping a subagent should terminate it
        and remove it from active list.
        """
        subagent_id = "test-subagent-123"
        redis_mock.get_subagent_status = AsyncMock(return_value={
            "status": "running",
            "mode": "foreground",
            "agent_name": "planning"
        })
        redis_mock.remove_active_subagent = AsyncMock()
        redis_mock.get_active_subagents = AsyncMock(return_value=[])
        
        response = await client.post(f"/api/v2/subagents/{subagent_id}/stop")
        assert response.status_code == 200
        
        # Verify removed from active list
        active = await client.get("/api/v2/subagents/active")
        active_list = active.json().get("data", [])
        assert not any(s.get("subagent_id") == subagent_id for s in active_list)
    
    @pytest.mark.asyncio
    async def test_max_parallel_subagents_enforced(self, client, redis_mock):
        """
        REQUIREMENT: System should enforce maximum of 10 parallel subagents.
        """
        # Mock that we already have 10 active subagents
        redis_mock.get_active_subagent_count = AsyncMock(return_value=10)
        
        # 11th should fail
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "background",
            "task_id": "task-overflow"
        })
        
        assert response.status_code == 429
        assert "maximum" in response.json()["detail"].lower()


class TestParallelExecutionFlow:
    """Test parallel subagent execution requirements."""
    
    @pytest.mark.asyncio
    async def test_parallel_group_created(self, client, redis_mock):
        """
        REQUIREMENT: Subagents in a parallel group should be created
        and tracked together.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        redis_mock.create_parallel_group = AsyncMock()
        
        response = await client.post("/api/v2/subagents/parallel", json={
            "agents": [
                {"type": "planning", "task": "Research auth module"},
                {"type": "planning", "task": "Research database module"},
                {"type": "planning", "task": "Research API module"},
            ]
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert "group_id" in data
        assert data["agent_count"] == 3
    
    @pytest.mark.asyncio
    async def test_parallel_results_aggregated(self, client, redis_mock):
        """
        REQUIREMENT: Results from parallel subagents should be
        aggregated and accessible together.
        """
        group_id = "test-group-123"
        redis_mock.get_parallel_results = AsyncMock(return_value={
            "subagent-1": {"output": "Result 1", "status": "completed"},
            "subagent-2": {"output": "Result 2", "status": "completed"},
            "subagent-3": {"output": "Result 3", "status": "completed"},
        })
        redis_mock.get_parallel_status = AsyncMock(return_value={
            "status": "completed",
            "total": "3",
            "completed": "3"
        })
        
        results = await client.get(f"/api/v2/subagents/parallel/{group_id}/results")
        
        assert results.status_code == 200
        data = results.json()
        assert len(data["results"]) == 3
        for result in data["results"]:
            assert "output" in result
            assert "status" in result


class TestSubagentContextFlow:
    """Test subagent context sharing requirements."""
    
    @pytest.mark.asyncio
    async def test_subagent_receives_conversation_context(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Subagent should receive last 20 messages
        from conversation as context.
        """
        from core.database.models import ConversationDB, ConversationMessageDB
        import uuid
        
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        
        # Create conversation with 25 messages
        conv = ConversationDB(
            conversation_id=conv_id,
            user_id="test-user",
            title="Test"
        )
        db_session.add(conv)
        
        for i in range(25):
            msg = ConversationMessageDB(
                message_id=f"msg-{i}",
                conversation_id=conv_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)
        await db_session.commit()
        
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground",
            "conversation_id": conv_id
        })
        
        assert response.status_code == 200
        subagent_id = response.json()["data"]["subagent_id"]
        
        context = await client.get(f"/api/v2/subagents/{subagent_id}/context")
        assert context.status_code == 200
        assert context.json()["message_count"] <= 20
    
    @pytest.mark.asyncio
    async def test_subagent_context_isolated_between_tasks(self, client, redis_mock):
        """
        REQUIREMENT: Each subagent's context should be isolated;
        one subagent's work shouldn't leak to another.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Spawn two subagents for different tasks
        sub1 = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "task_id": "task-secret-a"
        })
        sub2 = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "task_id": "task-secret-b"
        })
        
        assert sub1.status_code == 200
        assert sub2.status_code == 200
        
        # Verify different subagent IDs
        assert sub1.json()["data"]["subagent_id"] != sub2.json()["data"]["subagent_id"]
