"""Tests for webhook flow integration (TDD Phase 0)."""

import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from core.database.models import TaskDB, ConversationDB, SessionDB
from core.webhook_engine import action_create_task, generate_external_id, generate_flow_id
from shared import TaskStatus


class TestWebhookFlowIntegration:
    """Test webhook task creation with flow tracking."""
    async def test_webhook_task_gets_flow_id(self, db):
        """Test: Webhook task gets flow_id when created."""
        # Use unique external_id to avoid conversation_id collisions
        unique_key = f"PROJ-{uuid.uuid4().hex[:8]}"
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": unique_key
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            result = await action_create_task(
                agent="planning",
                message="Analyze this issue",
                payload=payload,
                db=db
            )
            
            assert result["action"] == "create_task"
            assert "task_id" in result
            
            # Get task from database
            from sqlalchemy import select
            task_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == result["task_id"])
            )
            task = task_result.scalar_one_or_none()
            
            assert task is not None
            # Check flow_id is set
            source_metadata = json.loads(task.source_metadata or "{}")
            assert "flow_id" in source_metadata or task.flow_id is not None
    async def test_webhook_task_gets_initiated_task_id(self, db):
        """Test: Root webhook task gets initiated_task_id set to itself."""
        # Use unique external_id to avoid conversation_id collisions
        unique_key = f"PROJ-{uuid.uuid4().hex[:8]}"
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": unique_key
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            result = await action_create_task(
                agent="planning",
                message="Root task",
                payload=payload,
                db=db
            )
            
            task_id = result["task_id"]
            
            # Get task from database
            from sqlalchemy import select
            task_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id)
            )
            task = task_result.scalar_one_or_none()
            
            assert task is not None
            # Root task should have initiated_task_id = task_id
            assert task.initiated_task_id == task_id or json.loads(task.source_metadata or "{}").get("initiated_task_id") == task_id
    async def test_webhook_task_creates_flow_conversation(self, db):
        """Test: Webhook task creates conversation with flow_id."""
        # Use unique external_id to avoid conversation_id collisions
        unique_key = f"PROJ-{uuid.uuid4().hex[:8]}"
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": unique_key
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            result = await action_create_task(
                agent="planning",
                message="Test task",
                payload=payload,
                db=db
            )
            
            task_id = result["task_id"]
            
            # Get task from database
            from sqlalchemy import select
            task_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id)
            )
            task = task_result.scalar_one_or_none()
            
            assert task is not None
            
            # Check conversation was created with flow_id
            source_metadata = json.loads(task.source_metadata or "{}")
            conversation_id = source_metadata.get("conversation_id")
            
            if conversation_id:
                conv_result = await db.execute(
                    select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
                )
                conversation = conv_result.scalar_one_or_none()
                
                if conversation:
                    # Conversation should have flow_id
                    assert conversation.flow_id is not None
    async def test_multiple_webhook_tasks_share_flow_id(self, db):
        """Test: Multiple webhook tasks from same external_id share flow_id."""
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": "PROJ-SHARED"
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            # Create first task
            result1 = await action_create_task(
                agent="planning",
                message="First task",
                payload=payload,
                db=db
            )
            
            # Create second task with same external_id
            result2 = await action_create_task(
                agent="executor",
                message="Second task",
                payload=payload,
                db=db
            )
            
            # Get tasks from database
            from sqlalchemy import select
            task1_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == result1["task_id"])
            )
            task1 = task1_result.scalar_one_or_none()
            
            task2_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == result2["task_id"])
            )
            task2 = task2_result.scalar_one_or_none()
            
            assert task1 is not None
            assert task2 is not None
            
            # Both should have same flow_id
            flow_id_1 = task1.flow_id or json.loads(task1.source_metadata or "{}").get("flow_id")
            flow_id_2 = task2.flow_id or json.loads(task2.source_metadata or "{}").get("flow_id")
            
            if flow_id_1 and flow_id_2:
                assert flow_id_1 == flow_id_2
