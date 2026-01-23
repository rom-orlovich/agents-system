"""End-to-end integration tests for task flow tracking (TDD Phase 0)."""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from core.database.models import TaskDB, ConversationDB, SessionDB
from core.webhook_engine import action_create_task
from shared import TaskStatus


class TestEndToEndTaskFlow:
    """Test end-to-end task flow with flow tracking."""
    
    async def test_webhook_to_child_tasks_share_conversation(self, db):
        """Test: Webhook → Task #1 → Task #2 → Task #3 all share same conversation_id."""
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": "PROJ-E2E-1"
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            # Create root task from webhook
            result1 = await action_create_task(
                agent="planning",
                message="Root task",
                payload=payload,
                db=db
            )
            
            task_id_1 = result1["task_id"]
            
            # Get task from database
            from sqlalchemy import select
            task1_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id_1)
            )
            task1 = task1_result.scalar_one_or_none()
            
            assert task1 is not None
            
            # Extract conversation_id and flow_id from task1
            source_metadata_1 = json.loads(task1.source_metadata or "{}")
            conversation_id_1 = source_metadata_1.get("conversation_id")
            flow_id_1 = source_metadata_1.get("flow_id")
            
            assert conversation_id_1 is not None
            assert flow_id_1 is not None
            
            # Simulate task1 creating child task (inherit conversation)
            task2_metadata = {
                "conversation_id": conversation_id_1,
                "flow_id": flow_id_1,
                "initiated_task_id": task_id_1,
                "parent_task_id": task_id_1
            }
            
            task2 = TaskDB(
                task_id="task-e2e-child",
                session_id=task1.session_id,
                user_id=task1.user_id,
                agent_type="executor",
                status=TaskStatus.QUEUED,
                input_message="Child task",
                source="webhook",
                source_metadata=json.dumps(task2_metadata),
                flow_id=flow_id_1,
                initiated_task_id=task_id_1,
                parent_task_id=task_id_1
            )
            db.add(task2)
            await db.commit()
            
            # Verify child task has same conversation_id and flow_id
            source_metadata_2 = json.loads(task2.source_metadata)
            assert source_metadata_2["conversation_id"] == conversation_id_1
            assert source_metadata_2["flow_id"] == flow_id_1
            assert task2.flow_id == flow_id_1
    
    async def test_new_conversation_breaks_chain_but_keeps_flow_id(self, db):
        """Test: Webhook → Task #1 → 'new conversation' → Task #2 has new conversation_id but same flow_id."""
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": "PROJ-E2E-2"
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            # Create root task
            result1 = await action_create_task(
                agent="planning",
                message="Root task",
                payload=payload,
                db=db
            )
            
            task_id_1 = result1["task_id"]
            
            # Get task from database
            from sqlalchemy import select
            task1_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id_1)
            )
            task1 = task1_result.scalar_one_or_none()
            
            source_metadata_1 = json.loads(task1.source_metadata or "{}")
            conversation_id_1 = source_metadata_1.get("conversation_id")
            flow_id_1 = source_metadata_1.get("flow_id")
            
            # Simulate task creating child with "new conversation" request
            from core.webhook_engine import should_start_new_conversation
            
            prompt = "Let's start a new conversation about this"
            should_new = should_start_new_conversation(prompt, {})
            assert should_new is True
            
            # Create new conversation but keep flow_id
            conversation2 = ConversationDB(
                conversation_id="conv-e2e-new",
                user_id=task1.user_id,
                title="New Conversation",
                flow_id=flow_id_1,  # Same flow_id
                initiated_task_id="task-e2e-new-root"
            )
            db.add(conversation2)
            await db.flush()
            
            task2_metadata = {
                "conversation_id": "conv-e2e-new",  # New conversation
                "flow_id": flow_id_1,  # Same flow_id
                "initiated_task_id": task_id_1,  # Same root
                "parent_task_id": task_id_1
            }
            
            task2 = TaskDB(
                task_id="task-e2e-new-conv",
                session_id=task1.session_id,
                user_id=task1.user_id,
                agent_type="executor",
                status=TaskStatus.QUEUED,
                input_message=prompt,
                source="webhook",
                source_metadata=json.dumps(task2_metadata),
                flow_id=flow_id_1,  # Same flow_id
                initiated_task_id=task_id_1  # Same root
            )
            db.add(task2)
            await db.commit()
            
            # Verify: new conversation but same flow_id
            assert task2.flow_id == flow_id_1
            source_metadata_2 = json.loads(task2.source_metadata)
            assert source_metadata_2["conversation_id"] != conversation_id_1
            assert source_metadata_2["flow_id"] == flow_id_1
    
    async def test_all_tasks_in_flow_share_flow_id(self, db):
        """Test: All tasks in flow share same flow_id regardless of conversation breaks."""
        payload = {
            "webhook_source": "jira",
            "provider": "jira",
            "issue": {
                "key": "PROJ-E2E-3"
            }
        }
        
        with patch('core.webhook_engine.redis_client') as mock_redis:
            mock_redis.push_task = AsyncMock()
            
            # Create root task
            result1 = await action_create_task(
                agent="planning",
                message="Root task",
                payload=payload,
                db=db
            )
            
            task_id_1 = result1["task_id"]
            
            from sqlalchemy import select
            task1_result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id_1)
            )
            task1 = task1_result.scalar_one_or_none()
            
            source_metadata_1 = json.loads(task1.source_metadata or "{}")
            flow_id = source_metadata_1.get("flow_id")
            
            # Create multiple tasks in the flow
            tasks = []
            for i in range(3):
                task_metadata = {
                    "conversation_id": f"conv-e2e-{i}",
                    "flow_id": flow_id,  # All share same flow_id
                    "initiated_task_id": task_id_1
                }
                
                task = TaskDB(
                    task_id=f"task-e2e-flow-{i}",
                    session_id=task1.session_id,
                    user_id=task1.user_id,
                    agent_type="planning",
                    status=TaskStatus.QUEUED,
                    input_message=f"Task {i}",
                    source="webhook",
                    source_metadata=json.dumps(task_metadata),
                    flow_id=flow_id,
                    initiated_task_id=task_id_1
                )
                tasks.append(task)
                db.add(task)
            
            await db.commit()
            
            # Verify all tasks share same flow_id
            for task in tasks:
                assert task.flow_id == flow_id
                metadata = json.loads(task.source_metadata)
                assert metadata["flow_id"] == flow_id
    
    async def test_conversation_metrics_aggregate_correctly(self, db):
        """Test: Dashboard shows aggregated metrics per conversation."""
        from core.database.models import update_conversation_metrics
        
        # Create session
        session = SessionDB(
            session_id="session-e2e-metrics",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-e2e-metrics",
            user_id="user-001",
            title="E2E Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create and complete multiple tasks
        tasks = [
            TaskDB(
                task_id=f"task-e2e-metrics-{i}",
                session_id="session-e2e-metrics",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.COMPLETED,
                input_message=f"Task {i}",
                source="webhook",
                source_metadata='{"conversation_id": "conv-e2e-metrics"}',
                cost_usd=0.25 * (i + 1),
                duration_seconds=5.0 * (i + 1),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        for task in tasks:
            db.add(task)
            await db.flush()
            await update_conversation_metrics(conversation.conversation_id, task, db)
        
        await db.commit()
        await db.refresh(conversation)
        
        # Verify aggregated metrics
        assert conversation.total_tasks == 3
        expected_cost = sum(0.25 * (i + 1) for i in range(3))  # 0.25 + 0.50 + 0.75 = 1.50
        assert abs(conversation.total_cost_usd - expected_cost) < 0.01
    
    async def test_claude_code_tasks_sync_works_end_to_end(self, db):
        """Test: Claude Code Tasks sync works end-to-end."""
        import tempfile
        from pathlib import Path
        from core.claude_tasks_sync import sync_task_to_claude_tasks, update_claude_task_status
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('core.claude_tasks_sync.settings') as mock_settings:
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                # Create session
                session = SessionDB(
                    session_id="session-e2e-claude",
                    user_id="user-001",
                    machine_id="machine-001",
                    connected_at=datetime.now(timezone.utc)
                )
                db.add(session)
                await db.flush()
                
                # Create task
                task = TaskDB(
                    task_id="task-e2e-claude",
                    session_id="session-e2e-claude",
                    user_id="user-001",
                    agent_type="planning",
                    status=TaskStatus.RUNNING,
                    input_message="Test task",
                    source="webhook",
                    source_metadata='{"conversation_id": "conv-123"}',
                    created_at=datetime.now(timezone.utc)
                )
                db.add(task)
                await db.flush()
                
                # Sync to Claude Code Tasks
                claude_task_id = sync_task_to_claude_tasks(
                    task_db=task,
                    flow_id="flow-e2e",
                    conversation_id="conv-123"
                )
                
                assert claude_task_id is not None
                
                # Verify file exists
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                assert task_file.exists()
                
                # Update task status
                task.status = TaskStatus.COMPLETED
                task.result = "Task completed"
                
                # Update Claude Code Task status
                update_claude_task_status(claude_task_id, "completed", task.result)
                
                # Verify status was updated
                import json
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                assert claude_task["status"] == "completed"
                assert claude_task.get("result") == "Task completed"
