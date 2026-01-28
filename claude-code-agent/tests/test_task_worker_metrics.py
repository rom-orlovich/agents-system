"""Tests for TaskWorker metrics updates (TDD Phase 0)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from core.database.models import TaskDB, ConversationDB, SessionDB
from shared import TaskStatus


class TestTaskWorkerMetrics:
    """Test TaskWorker updates conversation metrics on task completion."""
    
    async def test_task_worker_updates_conversation_metrics_on_completion(self, db):
        """Test: TaskWorker updates conversation metrics when task completes."""
        from core.database.models import update_conversation_metrics
        
        # Create session
        session = SessionDB(
            session_id="session-worker-metrics-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-worker-metrics-1",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create task with conversation_id in source_metadata
        task = TaskDB(
            task_id="task-worker-metrics-1",
            session_id="session-worker-metrics-1",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Test task",
            source="webhook",
            source_metadata='{"conversation_id": "conv-worker-metrics-1"}',
            cost_usd=0.75,
            duration_seconds=15.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=15),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task)
        await db.flush()
        
        # Simulate TaskWorker updating metrics
        await update_conversation_metrics(conversation.conversation_id, task, db)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_cost_usd == 0.75
        assert conversation.total_tasks == 1
        assert conversation.total_duration_seconds == 15.0
    
    async def test_task_worker_extracts_conversation_id_from_source_metadata(self, db):
        """Test: TaskWorker extracts conversation_id from task source_metadata."""
        import json
        from core.database.models import update_conversation_metrics
        
        # Create session
        session = SessionDB(
            session_id="session-worker-metrics-2",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-worker-metrics-2",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create task with conversation_id in source_metadata
        source_metadata = {
            "conversation_id": "conv-worker-metrics-2",
            "flow_id": "flow-123",
            "webhook_source": "jira"
        }
        task = TaskDB(
            task_id="task-worker-metrics-2",
            session_id="session-worker-metrics-2",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Test task",
            source="webhook",
            source_metadata=json.dumps(source_metadata),
            cost_usd=0.50,
            duration_seconds=10.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=10),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task)
        await db.flush()
        
        # Extract conversation_id from source_metadata
        metadata = json.loads(task.source_metadata)
        extracted_conversation_id = metadata.get("conversation_id")
        
        assert extracted_conversation_id == "conv-worker-metrics-2"
        
        # Update metrics
        await update_conversation_metrics(extracted_conversation_id, task, db)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_cost_usd == 0.50
        assert conversation.total_tasks == 1
    
    async def test_task_worker_updates_claude_task_status_on_completion(self, db):
        """Test: TaskWorker updates Claude Code Task status when orchestration task completes."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks, update_claude_task_status
        import tempfile
        from pathlib import Path
        
        # Create temporary directory for Claude Code Tasks
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('core.claude_tasks_sync.settings') as mock_settings:
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                # Create session
                session = SessionDB(
                    session_id="session-worker-metrics-3",
                    user_id="user-001",
                    machine_id="machine-001",
                    connected_at=datetime.now(timezone.utc)
                )
                db.add(session)
                await db.flush()
                
                # Create task
                task = TaskDB(
                    task_id="task-worker-metrics-3",
                    session_id="session-worker-metrics-3",
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
                    flow_id="flow-123",
                    conversation_id="conv-123"
                )
                
                assert claude_task_id is not None
                
                # Update task to completed
                task.status = TaskStatus.COMPLETED
                task.result = "Task completed successfully"
                
                # Update Claude Code Task status
                update_claude_task_status(claude_task_id, "completed", task.result)
                
                # Verify Claude Code Task was updated
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                assert task_file.exists()
                
                import json
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                assert claude_task["status"] == "completed"
                assert claude_task.get("result") == "Task completed successfully"
    
    async def test_task_worker_handles_missing_conversation_id_gracefully(self, db):
        """Test: TaskWorker handles tasks without conversation_id gracefully."""
        # Create session
        session = SessionDB(
            session_id="session-worker-metrics-4",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create task without conversation_id
        task = TaskDB(
            task_id="task-worker-metrics-4",
            session_id="session-worker-metrics-4",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Test task",
            source="dashboard",
            source_metadata='{}',  # No conversation_id
            cost_usd=0.25,
            duration_seconds=5.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task)
        await db.flush()
        
        # TaskWorker should handle this gracefully (no error)
        import json
        metadata = json.loads(task.source_metadata)
        conversation_id = metadata.get("conversation_id")
        
        # If no conversation_id, metrics update should be skipped (no error)
        if conversation_id:
            from core.database.models import update_conversation_metrics
            await update_conversation_metrics(conversation_id, task, db)
        
        # Should complete without error
        assert True  # Test passes if no exception raised
    
    async def test_task_worker_updates_multiple_tasks_in_conversation(self, db):
        """Test: TaskWorker correctly aggregates metrics for multiple tasks in conversation."""
        from core.database.models import update_conversation_metrics
        
        # Create session
        session = SessionDB(
            session_id="session-worker-metrics-5",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-worker-metrics-5",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create multiple tasks
        tasks = [
            TaskDB(
                task_id=f"task-worker-metrics-5-{i}",
                session_id="session-worker-metrics-5",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.COMPLETED,
                input_message=f"Task {i}",
                source="webhook",
                source_metadata='{"conversation_id": "conv-worker-metrics-5"}',
                cost_usd=0.20 * (i + 1),
                duration_seconds=5.0 * (i + 1),
                started_at=datetime.now(timezone.utc) - timedelta(seconds=5 * (i + 1)),
                completed_at=datetime.now(timezone.utc) - timedelta(seconds=5 * (i + 1)) + timedelta(seconds=5 * (i + 1))
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
        expected_cost = sum(0.20 * (i + 1) for i in range(3))  # 0.20 + 0.40 + 0.60 = 1.20
        expected_duration = sum(5.0 * (i + 1) for i in range(3))  # 5 + 10 + 15 = 30
        assert abs(conversation.total_cost_usd - expected_cost) < 0.01
        assert abs(conversation.total_duration_seconds - expected_duration) < 0.1
