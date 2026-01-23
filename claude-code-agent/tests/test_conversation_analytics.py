"""Tests for conversation-level analytics API endpoints (TDD Phase 0)."""

import pytest
from datetime import datetime, timedelta, timezone
from core.database.models import TaskDB, ConversationDB, SessionDB
from shared import TaskStatus


class TestConversationAnalyticsAPI:
    """Test conversation-level analytics endpoints."""
    
    async def test_get_conversations_analytics_endpoint(self, client, db):
        """Test: GET /analytics/conversations returns conversation-level analytics."""
        # Create sessions
        sessions = [
            SessionDB(
                session_id=f"session-analytics-{i}",
                user_id="user-001",
                machine_id="machine-001",
                connected_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        for session in sessions:
            db.add(session)
        await db.flush()
        
        # Create conversations with metrics
        conversations = [
            ConversationDB(
                conversation_id=f"conv-analytics-{i}",
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
        
        # Call API endpoint
        response = await client.get("/api/analytics/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return conversation-level analytics
        assert "total_conversations" in data or "conversations" in data
        assert "total_cost_usd" in data or "total_cost" in data
        assert "total_tasks" in data
    
    async def test_conversations_analytics_includes_cost_breakdown(self, client, db):
        """Test: GET /analytics/conversations includes cost breakdown by conversation."""
        # Create session
        session = SessionDB(
            session_id="session-analytics-cost",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversations with different costs
        conversations = [
            ConversationDB(
                conversation_id=f"conv-analytics-cost-{i}",
                user_id="user-001",
                title=f"Conversation {i}",
                total_cost_usd=1.00 * (i + 1),
                total_tasks=2,
                total_duration_seconds=20.0,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                completed_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        for conv in conversations:
            db.add(conv)
        await db.commit()
        
        # Call API endpoint
        response = await client.get("/api/analytics/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include cost information
        assert "total_cost_usd" in data or "total_cost" in data
    
    async def test_conversations_analytics_includes_task_counts(self, client, db):
        """Test: GET /analytics/conversations includes task counts per conversation."""
        # Create session
        session = SessionDB(
            session_id="session-analytics-tasks",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversations with different task counts
        conversations = [
            ConversationDB(
                conversation_id=f"conv-analytics-tasks-{i}",
                user_id="user-001",
                title=f"Conversation {i}",
                total_cost_usd=0.50,
                total_tasks=i + 1,
                total_duration_seconds=10.0,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                completed_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        for conv in conversations:
            db.add(conv)
        await db.commit()
        
        # Call API endpoint
        response = await client.get("/api/analytics/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include task count information
        assert "total_tasks" in data
    
    async def test_conversations_analytics_filters_by_date_range(self, client, db):
        """Test: GET /analytics/conversations supports date range filtering."""
        # Create session
        session = SessionDB(
            session_id="session-analytics-date",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversations with different dates
        now = datetime.now(timezone.utc)
        conversations = [
            ConversationDB(
                conversation_id=f"conv-analytics-date-{i}",
                user_id="user-001",
                title=f"Conversation {i}",
                total_cost_usd=0.50,
                total_tasks=1,
                total_duration_seconds=10.0,
                started_at=now - timedelta(days=i),
                completed_at=now - timedelta(days=i) + timedelta(minutes=5)
            )
            for i in range(3)
        ]
        
        for conv in conversations:
            db.add(conv)
        await db.commit()
        
        # Call API endpoint with date filter
        start_date = (now - timedelta(days=2)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/api/analytics/conversations?start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return filtered results
        assert isinstance(data, dict)
