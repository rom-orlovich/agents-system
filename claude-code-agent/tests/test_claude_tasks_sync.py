"""Tests for Claude Code Tasks sync functionality (TDD Phase 0)."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from core.database.models import TaskDB, SessionDB
from shared import TaskStatus


class TestClaudeTasksSync:
    """Test Claude Code Tasks sync functionality."""
    
    def test_claude_task_created_when_orchestration_task_created(self, tmp_path):
        """Test: Claude Code task is created when orchestration task is created."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        
        # Mock settings
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            # Create a task
            task_db = TaskDB(
                task_id="task-123",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.QUEUED,
                input_message="Test task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            flow_id = "flow-abc"
            conversation_id = "conv-xyz"
            
            # Sync task
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id=flow_id,
                conversation_id=conversation_id
            )
            
            assert claude_task_id is not None
            assert isinstance(claude_task_id, str)
            
            # Check file was created
            task_file = tmp_path / f"{claude_task_id}.json"
            assert task_file.exists()
            
            # Check file contents
            with open(task_file) as f:
                claude_task = json.load(f)
            
            assert claude_task["id"] == claude_task_id
            assert claude_task["metadata"]["orchestration_task_id"] == "task-123"
            assert claude_task["metadata"]["flow_id"] == flow_id
            assert claude_task["metadata"]["conversation_id"] == conversation_id
    
    def test_claude_task_id_stored_in_source_metadata(self, tmp_path):
        """Test: Claude Code task ID is stored in source_metadata."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            task_db = TaskDB(
                task_id="task-456",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.QUEUED,
                input_message="Test task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id="flow-xyz",
                conversation_id="conv-abc"
            )
            
            # Check source_metadata was updated
            metadata = json.loads(task_db.source_metadata)
            assert metadata.get("claude_task_id") == claude_task_id
    
    def test_parent_child_relationships_sync_correctly(self, tmp_path):
        """Test: Parent-child relationships sync correctly to Claude Code Tasks."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            # Create parent task
            parent_task = TaskDB(
                task_id="task-parent",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.QUEUED,
                input_message="Parent task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            parent_claude_id = sync_task_to_claude_tasks(
                task_db=parent_task,
                flow_id="flow-123",
                conversation_id="conv-123"
            )
            
            # Create child task with parent reference
            child_task = TaskDB(
                task_id="task-child",
                session_id="session-001",
                user_id="user-001",
                agent_type="executor",
                status=TaskStatus.QUEUED,
                input_message="Child task",
                source="webhook",
                parent_task_id="task-parent",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            child_claude_id = sync_task_to_claude_tasks(
                task_db=child_task,
                flow_id="flow-123",
                conversation_id="conv-123",
                parent_claude_task_id=parent_claude_id
            )
            
            # Check child task has parent dependency
            child_file = tmp_path / f"{child_claude_id}.json"
            with open(child_file) as f:
                child_claude_task = json.load(f)
            
            assert parent_claude_id in child_claude_task["dependencies"]
    
    def test_flow_tracking_metadata_preserved(self, tmp_path):
        """Test: Flow tracking metadata (flow_id, conversation_id) is preserved in Claude Code task metadata."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            task_db = TaskDB(
                task_id="task-789",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.QUEUED,
                input_message="Test task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            flow_id = "flow-test-123"
            conversation_id = "conv-test-456"
            
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id=flow_id,
                conversation_id=conversation_id
            )
            
            task_file = tmp_path / f"{claude_task_id}.json"
            with open(task_file) as f:
                claude_task = json.load(f)
            
            assert claude_task["metadata"]["flow_id"] == flow_id
            assert claude_task["metadata"]["conversation_id"] == conversation_id
            assert claude_task["metadata"]["orchestration_task_id"] == "task-789"
    
    def test_claude_task_status_updates_when_task_completes(self, tmp_path):
        """Test: Claude Code task status updates when orchestration task completes."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks, update_claude_task_status
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            # Create and sync task
            task_db = TaskDB(
                task_id="task-complete",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.RUNNING,
                input_message="Test task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id="flow-123",
                conversation_id="conv-123"
            )
            
            # Update task status to completed
            task_db.status = TaskStatus.COMPLETED
            task_db.result = "Task completed successfully"
            
            update_claude_task_status(claude_task_id, "completed", task_db.result)
            
            # Check status was updated
            task_file = tmp_path / f"{claude_task_id}.json"
            with open(task_file) as f:
                claude_task = json.load(f)
            
            assert claude_task["status"] == "completed"
    
    def test_sync_disabled_when_setting_false(self, tmp_path):
        """Test: Sync doesn't happen when sync_to_claude_tasks is False."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = False
            mock_settings.claude_tasks_directory = tmp_path
            
            task_db = TaskDB(
                task_id="task-no-sync",
                session_id="session-001",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.QUEUED,
                input_message="Test task",
                source="webhook",
                source_metadata=json.dumps({}),
                created_at=datetime.now(timezone.utc)
            )
            
            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id="flow-123",
                conversation_id="conv-123"
            )
            
            assert claude_task_id is None
            
            # Check no files were created
            assert len(list(tmp_path.glob("*.json"))) == 0
    
    def test_status_mapping_correct(self, tmp_path):
        """Test: Status mapping between TaskStatus and Claude Code task status is correct."""
        from core.claude_tasks_sync import sync_task_to_claude_tasks, update_claude_task_status
        
        with patch('core.claude_tasks_sync.settings') as mock_settings:
            mock_settings.sync_to_claude_tasks = True
            mock_settings.claude_tasks_directory = tmp_path
            
            # Test different statuses
            status_mappings = [
                (TaskStatus.QUEUED, "pending"),
                (TaskStatus.RUNNING, "in_progress"),
                (TaskStatus.COMPLETED, "completed"),
                (TaskStatus.FAILED, "failed"),
            ]
            
            for task_status, expected_claude_status in status_mappings:
                task_db = TaskDB(
                    task_id=f"task-{task_status}",
                    session_id="session-001",
                    user_id="user-001",
                    agent_type="planning",
                    status=task_status,
                    input_message="Test task",
                    source="webhook",
                    source_metadata=json.dumps({}),
                    created_at=datetime.now(timezone.utc)
                )
                
                claude_task_id = sync_task_to_claude_tasks(
                    task_db=task_db,
                    flow_id="flow-123",
                    conversation_id="conv-123"
                )
                
                task_file = tmp_path / f"{claude_task_id}.json"
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                assert claude_task["status"] == expected_claude_status, \
                    f"Status mapping failed: {task_status} -> {claude_task['status']} (expected {expected_claude_status})"
