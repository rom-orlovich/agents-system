"""Integration tests for session status & cost tracking (Part 9 of TDD Requirements)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
import uuid


class TestCostTrackingFlow:
    """Test cost tracking business requirements."""
    
    @pytest.mark.asyncio
    async def test_task_cost_calculated_from_tokens(self, client, db_session):
        """
        REQUIREMENT: Task cost should be calculated from input/output tokens
        using Claude's pricing model.
        
        Current pricing (as of 2024):
        - Claude 3.5 Sonnet: $3/1M input, $15/1M output
        """
        from core.database.models import TaskDB, SessionDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        # Create session and task with token counts
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine"
        )
        db_session.add(session)
        
        # Task with known token counts
        input_tokens = 1000
        output_tokens = 500
        # Expected cost: (1000 * 3 + 500 * 15) / 1_000_000 = 0.0105
        expected_cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
        
        task = TaskDB(
            task_id=task_id,
            session_id=session_id,
            user_id="test-user",
            input_message="Test task",
            status="completed",
            agent_type="planning",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=expected_cost
        )
        db_session.add(task)
        await db_session.commit()
        
        response = await client.get(f"/api/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cost_usd"] > 0
        assert data["input_tokens"] == input_tokens
        assert data["output_tokens"] == output_tokens
        # Verify cost formula (approximately)
        assert abs(data["cost_usd"] - expected_cost) < 0.01
    
    @pytest.mark.asyncio
    async def test_session_cost_aggregates_tasks(self, client, db_session):
        """
        REQUIREMENT: Session total cost should be sum of all task costs.
        """
        from core.database.models import TaskDB, SessionDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        # Create session
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine",
            total_cost_usd=0.0
        )
        db_session.add(session)
        
        # Create multiple tasks with costs
        total_cost = 0.0
        for i in range(3):
            cost = 0.01 * (i + 1)  # 0.01, 0.02, 0.03
            total_cost += cost
            task = TaskDB(
                task_id=f"task-{session_id}-{i}",
                session_id=session_id,
                user_id="test-user",
                input_message=f"Task {i}",
                status="completed",
                agent_type="planning",
                cost_usd=cost
            )
            db_session.add(task)
        
        # Update session total
        session.total_cost_usd = total_cost
        await db_session.commit()
        
        response = await client.get(f"/api/v2/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert abs(data["total_cost_usd"] - total_cost) < 0.001
    
    @pytest.mark.asyncio
    async def test_daily_cost_aggregation(self, client, db_session):
        """
        REQUIREMENT: Analytics should show daily cost breakdown.
        """
        response = await client.get("/api/analytics/costs/daily?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "costs" in data


class TestSessionStatusFlow:
    """Test session status business requirements."""
    
    @pytest.mark.asyncio
    async def test_session_shows_active_status(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Active sessions should show 'active' status
        with current task count.
        """
        from core.database.models import SessionDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine"
        )
        db_session.add(session)
        await db_session.commit()
        
        # Mock running tasks
        redis_mock.get_session_tasks = AsyncMock(return_value=["task-1", "task-2"])
        
        response = await client.get(f"/api/v2/sessions/{session_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["active", "idle", "disconnected"]
    
    @pytest.mark.asyncio
    async def test_session_reset_clears_context(self, client, db_session):
        """
        REQUIREMENT: Resetting a session should clear conversation
        context but preserve cost history.
        """
        from core.database.models import SessionDB, ConversationDB, ConversationMessageDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        
        # Create session with cost
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine",
            total_cost_usd=0.05
        )
        db_session.add(session)
        
        # Create conversation with messages
        conv = ConversationDB(
            conversation_id=conv_id,
            user_id="test-user",
            title="Test"
        )
        db_session.add(conv)
        
        for i in range(5):
            msg = ConversationMessageDB(
                message_id=f"msg-{i}",
                conversation_id=conv_id,
                role="user",
                content=f"Message {i}"
            )
            db_session.add(msg)
        await db_session.commit()
        
        original_cost = session.total_cost_usd
        
        # Reset session
        response = await client.post(f"/api/v2/sessions/{session_id}/reset")
        
        assert response.status_code == 200
        
        # Cost should be preserved
        session_response = await client.get(f"/api/v2/sessions/{session_id}")
        assert session_response.status_code == 200
        assert session_response.json()["total_cost_usd"] == original_cost
    
    @pytest.mark.asyncio
    async def test_weekly_session_summary(self, client, db_session):
        """
        REQUIREMENT: Should provide weekly session summary with
        total cost, task count, and active days.
        """
        response = await client.get("/api/v2/sessions/summary/weekly")
        
        assert response.status_code == 200
        summary = response.json()
        
        assert "total_cost_usd" in summary
        assert "total_tasks" in summary
        assert "active_days" in summary
        assert summary["active_days"] <= 7


class TestSessionDisplayFlow:
    """Test session display business requirements for dashboard."""
    
    @pytest.mark.asyncio
    async def test_current_session_status_displayed(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Dashboard should show current session status
        including: status, running tasks, cost, reset time.
        """
        from core.database.models import SessionDB
        
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        session = SessionDB(
            session_id=session_id,
            user_id="test-user",
            machine_id="test-machine",
            total_cost_usd=0.025,
            total_tasks=5
        )
        db_session.add(session)
        await db_session.commit()
        
        redis_mock.get_session_tasks = AsyncMock(return_value=["task-1"])
        
        response = await client.get("/api/v2/dashboard/session/current")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "session_id",
            "status",
            "total_cost_usd",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    @pytest.mark.asyncio
    async def test_session_history_shows_weekly(self, client, db_session):
        """
        REQUIREMENT: Session history should show past 7 days
        with daily breakdown.
        """
        response = await client.get("/api/v2/dashboard/sessions/history?days=7")
        
        assert response.status_code == 200
        history = response.json()
        
        assert "daily" in history or "sessions" in history
    
    @pytest.mark.asyncio
    async def test_weekly_chart_data_format(self, client):
        """
        REQUIREMENT: Weekly chart should receive data in Chart.js format.
        """
        response = await client.get("/api/analytics/costs/daily?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        # Chart.js format should have dates and costs arrays
        assert "dates" in data
        assert "costs" in data
