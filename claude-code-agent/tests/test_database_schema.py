"""Tests for database schema changes (TDD Phase 0)."""

import pytest
from datetime import datetime, timezone
from core.database.models import TaskDB, ConversationDB, SessionDB


class TestTaskDBSchema:
    """Test TaskDB schema has flow tracking fields."""
    async def test_task_has_flow_id_field(self, db):
        """Test: TaskDB has flow_id field."""
        session = SessionDB(
            session_id="session-schema-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-schema-1",
            session_id="session-schema-1",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Test task",
            source="webhook",
            source_metadata='{"flow_id": "flow-123"}',
            flow_id="flow-123"
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        assert task.flow_id == "flow-123"
        assert hasattr(task, 'flow_id')
    async def test_task_has_initiated_task_id_field(self, db):
        """Test: TaskDB has initiated_task_id field."""
        session = SessionDB(
            session_id="session-schema-2",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-schema-2",
            session_id="session-schema-2",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Test task",
            source="webhook",
            source_metadata='{}',
            initiated_task_id="task-root"
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        assert task.initiated_task_id == "task-root"
        assert hasattr(task, 'initiated_task_id')
    async def test_task_flow_id_can_be_null(self, db):
        """Test: TaskDB flow_id can be null (for backward compatibility)."""
        session = SessionDB(
            session_id="session-schema-3",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-schema-3",
            session_id="session-schema-3",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Test task",
            source="webhook",
            source_metadata='{}',
            flow_id=None
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        assert task.flow_id is None


class TestConversationDBSchema:
    """Test ConversationDB schema has flow tracking and metrics fields."""
    async def test_conversation_has_flow_id_field(self, db):
        """Test: ConversationDB has flow_id field."""
        conversation = ConversationDB(
            conversation_id="conv-schema-1",
            user_id="user-001",
            title="Test Conversation",
            flow_id="flow-abc"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.flow_id == "flow-abc"
        assert hasattr(conversation, 'flow_id')
    async def test_conversation_has_initiated_task_id_field(self, db):
        """Test: ConversationDB has initiated_task_id field."""
        conversation = ConversationDB(
            conversation_id="conv-schema-2",
            user_id="user-001",
            title="Test Conversation",
            initiated_task_id="task-root"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.initiated_task_id == "task-root"
        assert hasattr(conversation, 'initiated_task_id')
    async def test_conversation_has_total_cost_usd_field(self, db):
        """Test: ConversationDB has total_cost_usd field."""
        conversation = ConversationDB(
            conversation_id="conv-schema-3",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=1.50
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_cost_usd == 1.50
        assert hasattr(conversation, 'total_cost_usd')
    async def test_conversation_has_total_tasks_field(self, db):
        """Test: ConversationDB has total_tasks field."""
        conversation = ConversationDB(
            conversation_id="conv-schema-4",
            user_id="user-001",
            title="Test Conversation",
            total_tasks=5
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_tasks == 5
        assert hasattr(conversation, 'total_tasks')
    async def test_conversation_has_total_duration_seconds_field(self, db):
        """Test: ConversationDB has total_duration_seconds field."""
        conversation = ConversationDB(
            conversation_id="conv-schema-5",
            user_id="user-001",
            title="Test Conversation",
            total_duration_seconds=120.5
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_duration_seconds == 120.5
        assert hasattr(conversation, 'total_duration_seconds')
    async def test_conversation_has_started_at_field(self, db):
        """Test: ConversationDB has started_at field."""
        started_time = datetime.now(timezone.utc)
        conversation = ConversationDB(
            conversation_id="conv-schema-6",
            user_id="user-001",
            title="Test Conversation",
            started_at=started_time
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.started_at is not None
        # SQLite returns naive datetimes, so convert to UTC-aware for comparison
        db_time = conversation.started_at
        if db_time.tzinfo is None:
            db_time = db_time.replace(tzinfo=timezone.utc)
        assert abs((db_time - started_time).total_seconds()) < 1
        assert hasattr(conversation, 'started_at')
    async def test_conversation_has_completed_at_field(self, db):
        """Test: ConversationDB has completed_at field."""
        completed_time = datetime.now(timezone.utc)
        conversation = ConversationDB(
            conversation_id="conv-schema-7",
            user_id="user-001",
            title="Test Conversation",
            completed_at=completed_time
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.completed_at is not None
        # SQLite returns naive datetimes, so convert to UTC-aware for comparison
        db_time = conversation.completed_at
        if db_time.tzinfo is None:
            db_time = db_time.replace(tzinfo=timezone.utc)
        assert abs((db_time - completed_time).total_seconds()) < 1
        assert hasattr(conversation, 'completed_at')
    async def test_conversation_metrics_default_to_zero(self, db):
        """Test: ConversationDB metrics default to zero."""
        conversation = ConversationDB(
            conversation_id="conv-schema-8",
            user_id="user-001",
            title="Test Conversation"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_cost_usd == 0.0
        assert conversation.total_tasks == 0
        assert conversation.total_duration_seconds == 0.0
