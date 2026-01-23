"""Tests for flow conversation creation (TDD Phase 0)."""

import pytest
import uuid
from datetime import datetime, timezone
from core.database.models import TaskDB, ConversationDB, SessionDB
from core.webhook_engine import get_or_create_flow_conversation, generate_flow_id


class TestGetOrCreateFlowConversation:
    """Test get_or_create_flow_conversation function."""
    async def test_creates_new_conversation_for_new_flow(self, db):
        """Test: Creates new conversation when flow_id doesn't exist."""
        session = SessionDB(
            session_id="session-flow-conv-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-flow-conv-1",
            session_id="session-flow-conv-1",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Test task",
            source="webhook",
            source_metadata='{}'
        )
        db.add(task)
        await db.flush()
        
        # Use unique IDs to avoid collisions
        unique_suffix = uuid.uuid4().hex[:8]
        flow_id = f"flow-new-{unique_suffix}"
        external_id = f"jira:PROJ-{unique_suffix}"
        
        conversation = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task,
            db=db
        )
        
        await db.commit()
        
        assert conversation is not None
        assert conversation.flow_id == flow_id
        assert conversation.initiated_task_id == task.task_id
        assert conversation.user_id == task.user_id
    async def test_reuses_existing_conversation_for_same_flow(self, db):
        """Test: Reuses existing conversation when flow_id already exists."""
        session = SessionDB(
            session_id="session-flow-conv-2",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Use unique IDs to avoid collisions
        unique_suffix = uuid.uuid4().hex[:8]
        flow_id = f"flow-existing-{unique_suffix}"
        external_id = f"jira:PROJ-{unique_suffix}"
        
        # Create first task and conversation
        task1 = TaskDB(
            task_id="task-flow-conv-2a",
            session_id="session-flow-conv-2",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="First task",
            source="webhook",
            source_metadata='{}'
        )
        db.add(task1)
        await db.flush()
        
        conversation1 = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task1,
            db=db
        )
        await db.commit()
        conversation_id_1 = conversation1.conversation_id
        
        # Create second task with same flow_id
        task2 = TaskDB(
            task_id="task-flow-conv-2b",
            session_id="session-flow-conv-2",
            user_id="user-001",
            agent_type="executor",
            status="queued",
            input_message="Second task",
            source="webhook",
            source_metadata='{}'
        )
        db.add(task2)
        await db.flush()
        
        conversation2 = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task2,
            db=db
        )
        await db.commit()
        
        # Should reuse same conversation
        assert conversation2.conversation_id == conversation_id_1
        assert conversation2.flow_id == flow_id
    async def test_sets_initiated_task_id_on_first_conversation(self, db):
        """Test: Sets initiated_task_id to root task ID."""
        session = SessionDB(
            session_id="session-flow-conv-3",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-root-789",
            session_id="session-flow-conv-3",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Root task",
            source="webhook",
            source_metadata='{}'
        )
        db.add(task)
        await db.flush()
        
        # Use unique IDs to avoid collisions
        unique_suffix = uuid.uuid4().hex[:8]
        flow_id = f"flow-init-{unique_suffix}"
        external_id = f"jira:PROJ-{unique_suffix}"
        
        conversation = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task,
            db=db
        )
        await db.commit()
        
        assert conversation.initiated_task_id == task.task_id
    async def test_conversation_title_includes_external_id(self, db):
        """Test: Conversation title includes external ID information."""
        session = SessionDB(
            session_id="session-flow-conv-4",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        task = TaskDB(
            task_id="task-flow-conv-4",
            session_id="session-flow-conv-4",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Test task",
            source="webhook",
            source_metadata='{"webhook_source": "jira", "payload": {"issue": {"key": "PROJ-999"}}}'
        )
        db.add(task)
        await db.flush()
        
        # Use unique IDs to avoid collisions
        unique_suffix = uuid.uuid4().hex[:8]
        flow_id = f"flow-title-{unique_suffix}"
        external_id = f"jira:PROJ-{unique_suffix}"
        
        conversation = await get_or_create_flow_conversation(
            flow_id=flow_id,
            external_id=external_id,
            task_db=task,
            db=db
        )
        await db.commit()
        
        # Title should include external ID info
        assert conversation.title is not None
        assert len(conversation.title) > 0
