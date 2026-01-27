"""Integration tests for Claude Tasks sync in webhook task creation (TDD)."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from core.database.models import TaskDB
from shared import TaskStatus


class TestClaudeTasksSyncIntegration:
    """Test that webhook task creation functions call sync and create files correctly."""
    
    async def test_create_github_task_calls_sync_and_creates_file_with_routing_metadata(self):
        """
        Business Rule: GitHub task creation must call sync_task_to_claude_tasks.
        Behavior: File is created at ~/.claude/tasks/claude-task-{task_id}.json with routing metadata.
        """
        from api.webhooks.github.utils import create_github_task
        from core.webhook_configs import GITHUB_WEBHOOK
        
        command = GITHUB_WEBHOOK.commands[0]
        payload = {
            "repository": {
                "owner": {"login": "test-org"},
                "name": "test-repo",
                "full_name": "test-org/test-repo"
            },
            "pull_request": {"number": 42}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock), \
                 patch('api.webhooks.github.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"), \
                 patch('core.claude_tasks_sync.settings') as mock_settings:
                
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                task_id = await create_github_task(
                    command,
                    payload,
                    db_mock,
                    completion_handler="api.webhooks.github.routes.handle_github_task_completion"
                )
                
                assert task_id is not None
                
                claude_task_id = f"claude-task-{task_id}"
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                
                assert task_file.exists(), "Claude task file should be created"
                
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                assert claude_task["id"] == claude_task_id
                assert "metadata" in claude_task
                assert "source_metadata" in claude_task["metadata"]
                
                source_metadata = claude_task["metadata"]["source_metadata"]
                assert "routing" in source_metadata
                routing = source_metadata["routing"]
                
                assert routing["owner"] == "test-org"
                assert routing["repo"] == "test-repo"
                assert routing["pr_number"] == 42
    
    async def test_create_jira_task_calls_sync_with_routing_metadata(self):
        """
        Business Rule: Jira task creation must call sync_task_to_claude_tasks.
        Behavior: File is created with Jira routing metadata (ticket_key).
        """
        from api.webhooks.jira.utils import create_jira_task
        from core.webhook_configs import JIRA_WEBHOOK
        
        command = JIRA_WEBHOOK.commands[0]
        payload = {
            "issue": {
                "key": "PROJ-123",
                "fields": {"summary": "Test issue"}
            }
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock), \
                 patch('api.webhooks.jira.utils.redis_client.add_session_task', new_callable=AsyncMock), \
                 patch('api.webhooks.jira.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"), \
                 patch('core.claude_tasks_sync.settings') as mock_settings:
                
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                task_id = await create_jira_task(
                    command,
                    payload,
                    db_mock,
                    completion_handler="api.webhooks.jira.routes.handle_jira_task_completion"
                )
                
                assert task_id is not None
                
                claude_task_id = f"claude-task-{task_id}"
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                
                assert task_file.exists(), "Claude task file should be created"
                
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                source_metadata = claude_task["metadata"]["source_metadata"]
                assert "routing" in source_metadata
                routing = source_metadata["routing"]
                
                assert routing["ticket_key"] == "PROJ-123"
    
    async def test_create_slack_task_calls_sync_with_routing_metadata(self):
        """
        Business Rule: Slack task creation must call sync_task_to_claude_tasks.
        Behavior: File is created with Slack routing metadata (channel_id, thread_ts).
        """
        from api.webhooks.slack.utils import create_slack_task
        from core.webhook_configs import SLACK_WEBHOOK
        
        command = SLACK_WEBHOOK.commands[0]
        payload = {
            "event": {
                "channel": "C123456",
                "text": "@agent help",
                "user": "U123456",
                "ts": "1234567890.123456"
            }
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock), \
                 patch('api.webhooks.slack.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"), \
                 patch('core.claude_tasks_sync.settings') as mock_settings:
                
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                task_id = await create_slack_task(
                    command,
                    payload,
                    db_mock,
                    completion_handler="api.webhooks.slack.routes.handle_slack_task_completion"
                )
                
                assert task_id is not None
                
                claude_task_id = f"claude-task-{task_id}"
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                
                assert task_file.exists(), "Claude task file should be created"
                
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                source_metadata = claude_task["metadata"]["source_metadata"]
                assert "routing" in source_metadata
                routing = source_metadata["routing"]
                
                assert routing["channel_id"] == "C123456"
                assert "user_id" in routing
    
    async def test_webhook_engine_action_create_task_calls_sync(self):
        """
        Business Rule: webhook_engine.action_create_task must call sync_task_to_claude_tasks.
        Behavior: File is created when task is created via action_create_task.
        """
        from core.webhook_engine import action_create_task
        
        payload = {
            "webhook_source": "github",
            "repository": {
                "owner": {"login": "test-org"},
                "name": "test-repo",
                "full_name": "test-org/test-repo"
            },
            "issue": {"number": 99}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('core.webhook_engine.redis_client.push_task', new_callable=AsyncMock), \
                 patch('core.webhook_engine.get_or_create_flow_conversation', new_callable=AsyncMock) as mock_conv, \
                 patch('core.claude_tasks_sync.settings') as mock_settings:
                
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                from core.database.models import ConversationDB
                mock_conv.return_value = ConversationDB(
                    conversation_id="conv-123",
                    user_id="webhook-system",
                    title="Test",
                    flow_id="flow-123"
                )
                
                result = await action_create_task(
                    agent="brain",
                    message="Test task",
                    payload=payload,
                    db=db_mock
                )
                
                assert result["action"] == "create_task"
                task_id = result["task_id"]
                
                claude_task_id = f"claude-task-{task_id}"
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                
                assert task_file.exists(), "Claude task file should be created"
    
    async def test_created_file_contains_source_metadata_routing_for_github(self):
        """
        Business Rule: Created task file must contain source_metadata.routing with GitHub routing info.
        Behavior: Agents can extract owner, repo, pr_number from metadata.source_metadata.routing.
        """
        from api.webhooks.github.utils import create_github_task
        from core.webhook_configs import GITHUB_WEBHOOK
        
        command = GITHUB_WEBHOOK.commands[0]
        payload = {
            "repository": {
                "owner": {"login": "myorg"},
                "name": "myrepo",
                "full_name": "myorg/myrepo"
            },
            "pull_request": {"number": 100}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock), \
                 patch('api.webhooks.github.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"), \
                 patch('core.claude_tasks_sync.settings') as mock_settings:
                
                mock_settings.sync_to_claude_tasks = True
                mock_settings.claude_tasks_directory = Path(tmpdir)
                
                task_id = await create_github_task(
                    command,
                    payload,
                    db_mock,
                    completion_handler="api.webhooks.github.routes.handle_github_task_completion"
                )
                
                claude_task_id = f"claude-task-{task_id}"
                task_file = Path(tmpdir) / f"{claude_task_id}.json"
                
                with open(task_file) as f:
                    claude_task = json.load(f)
                
                metadata = claude_task["metadata"]
                assert "source_metadata" in metadata
                
                source_metadata = metadata["source_metadata"]
                assert "routing" in source_metadata
                
                routing = source_metadata["routing"]
                assert routing["owner"] == "myorg"
                assert routing["repo"] == "myrepo"
                assert routing["pr_number"] == 100
                
                assert "payload" in source_metadata
                assert source_metadata["webhook_source"] == "github"
    
    async def test_sync_failure_does_not_break_task_creation(self):
        """
        Business Rule: Sync failure must not break task creation.
        Behavior: Task is created successfully even if sync fails.
        """
        from api.webhooks.github.utils import create_github_task
        from core.webhook_configs import GITHUB_WEBHOOK
        
        command = GITHUB_WEBHOOK.commands[0]
        payload = {
            "repository": {
                "owner": {"login": "test"},
                "name": "repo",
                "full_name": "test/repo"
            },
            "issue": {"number": 1}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"), \
             patch('core.claude_tasks_sync.sync_task_to_claude_tasks') as mock_sync:
            
            mock_sync.side_effect = Exception("Sync failed")
            
            task_id = await create_github_task(
                command,
                payload,
                db_mock,
                completion_handler="api.webhooks.github.routes.handle_github_task_completion"
            )
            
            assert task_id is not None, "Task should be created even if sync fails"
            
            call_args = db_mock.add.call_args_list
            task_db = None
            for call in call_args:
                arg = call[0][0]
                if isinstance(arg, TaskDB):
                    task_db = arg
                    break
            
            assert task_db is not None
            assert task_db.task_id == task_id
