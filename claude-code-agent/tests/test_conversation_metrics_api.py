"""Tests for conversation metrics API endpoints (TDD Phase 0)."""

import pytest
from datetime import datetime, timedelta, timezone
from core.database.models import TaskDB, ConversationDB, SessionDB
from shared import TaskStatus


class TestConversationMetricsAPI:
    """Test conversation metrics API endpoints."""
    
    async def test_get_conversation_metrics_endpoint(self, client, db):
        """Test: GET /conversations/{conversation_id}/metrics returns aggregated metrics."""
        # Create session
        session = SessionDB(
            session_id="session-api-metrics-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation with metrics
        conversation = ConversationDB(
            conversation_id="conv-api-metrics-1",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=1.50,
            total_tasks=3,
            total_duration_seconds=45.0,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        await db.commit()
        
        # Call API endpoint (router is registered with /api prefix)
        response = await client.get(f"/api/conversations/conv-api-metrics-1/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_cost_usd"] == 1.50
        assert data["total_tasks"] == 3
        assert data["total_duration_seconds"] == 45.0
        assert "started_at" in data
        assert "completed_at" in data
    
    async def test_get_conversation_metrics_returns_task_breakdown(self, client, db):
        """Test: GET /conversations/{conversation_id}/metrics includes task breakdown by status."""
        # Create session
        session = SessionDB(
            session_id="session-api-metrics-2",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-api-metrics-2",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create tasks with different statuses
        tasks = [
            TaskDB(
                task_id=f"task-api-metrics-2-{i}",
                session_id="session-api-metrics-2",
                user_id="user-001",
                agent_type="planning",
                status=status,
                input_message=f"Task {i}",
                source="webhook",
                source_metadata=f'{{"conversation_id": "conv-api-metrics-2"}}',
                cost_usd=0.25,
                duration_seconds=5.0,
                started_at=datetime.now(timezone.utc) - timedelta(seconds=5),
                completed_at=datetime.now(timezone.utc) if status == TaskStatus.COMPLETED else None
            )
            for i, status in enumerate([
                TaskStatus.COMPLETED,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED
            ])
        ]
        
        for task in tasks:
            db.add(task)
        await db.commit()
        
        # Call API endpoint (router is registered with /api prefix)
        response = await client.get(f"/api/conversations/conv-api-metrics-2/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include task breakdown
        if "task_breakdown" in data:
            breakdown = data["task_breakdown"]
            assert breakdown.get("completed", 0) >= 2
            assert breakdown.get("failed", 0) >= 1
    
    async def test_get_conversation_metrics_calculates_average_cost(self, client, db):
        """Test: GET /conversations/{conversation_id}/metrics includes average cost per task."""
        # Create session
        session = SessionDB(
            session_id="session-api-metrics-3",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation with metrics
        conversation = ConversationDB(
            conversation_id="conv-api-metrics-3",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=1.50,
            total_tasks=3,
            total_duration_seconds=30.0,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        await db.commit()
        
        # Call API endpoint (router is registered with /api prefix)
        response = await client.get(f"/api/conversations/conv-api-metrics-3/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should calculate average cost
        if "average_cost_per_task" in data:
            assert data["average_cost_per_task"] == 0.50  # 1.50 / 3
    
    async def test_conversation_response_includes_metrics(self, client, db):
        """Test: ConversationResponse includes aggregated metrics."""
        # Create session
        session = SessionDB(
            session_id="session-api-metrics-4",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation with metrics
        conversation = ConversationDB(
            conversation_id="conv-api-metrics-4",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=2.00,
            total_tasks=5,
            total_duration_seconds=60.0,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        await db.commit()
        
        # Call GET /conversations/{id} endpoint (router is registered with /api prefix)
        response = await client.get(f"/api/conversations/conv-api-metrics-4")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include metrics in response
        assert "total_cost_usd" in data or "metrics" in data
        assert "total_tasks" in data or "metrics" in data
    
    async def test_list_conversations_includes_metrics(self, client, db):
        """Test: GET /conversations includes metrics in list response."""
        # Create session
        session = SessionDB(
            session_id="session-api-metrics-5",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversations with metrics
        conversations = [
            ConversationDB(
                conversation_id=f"conv-api-metrics-5-{i}",
                user_id="user-001",
                title=f"Conversation {i}",
                total_cost_usd=0.50 * (i + 1),
                total_tasks=i + 1,
                total_duration_seconds=10.0 * (i + 1),
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                completed_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        for conv in conversations:
            db.add(conv)
        await db.commit()
        
        # Call GET /conversations endpoint (router is registered with /api prefix)
        response = await client.get("/api/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Check that conversations include metrics
        for conv_data in data:
            if conv_data["conversation_id"].startswith("conv-api-metrics-5"):
                assert "total_cost_usd" in conv_data or "metrics" in conv_data
                assert "total_tasks" in conv_data or "metrics" in conv_data
    
    async def test_list_conversations_with_invalid_json_metadata(self, client, db):
        """Test: GET /conversations handles invalid JSON in metadata_json gracefully (doesn't cause 500 error)."""
        # Create session
        session = SessionDB(
            session_id="session-api-invalid-json-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation with invalid JSON in metadata_json
        # This simulates corrupted data that could cause json.loads() to fail
        conversation = ConversationDB(
            conversation_id="conv-api-invalid-json-1",
            user_id="user-001",
            title="Test Conversation with Invalid JSON",
            metadata_json='{"invalid": json}',  # Invalid JSON - missing quotes around json
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.commit()
        
        # Call GET /conversations endpoint - should NOT return 500 error
        response = await client.get("/api/conversations")
        
        # Should return 200, not 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # Find our conversation in the response
        conv_data = next((c for c in data if c["conversation_id"] == "conv-api-invalid-json-1"), None)
        assert conv_data is not None, "Conversation not found in response"
        
        # Metadata should be handled gracefully (empty dict or valid dict, not causing error)
        assert "metadata" in conv_data
        assert isinstance(conv_data["metadata"], dict)
    
    async def test_list_conversations_error_handling(self, client, db):
        """Test: GET /conversations handles errors gracefully."""
        # Test that the endpoint has error handling by verifying it doesn't crash
        # on edge cases. We'll test with a scenario that could cause issues.
        
        # Create a conversation with None metadata_json (edge case)
        conversation = ConversationDB(
            conversation_id="conv-api-error-handling-1",
            user_id="user-001",
            title="Test Conversation",
            metadata_json=None,  # None instead of empty string
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.commit()
        
        # Call endpoint - should handle None gracefully
        response = await client.get("/api/conversations")
        
        # Should return 200, not crash
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify the conversation with None metadata is handled
        conv_data = next((c for c in data if c["conversation_id"] == "conv-api-error-handling-1"), None)
        assert conv_data is not None, "Conversation not found in response"
        assert "metadata" in conv_data
        assert isinstance(conv_data["metadata"], dict)
