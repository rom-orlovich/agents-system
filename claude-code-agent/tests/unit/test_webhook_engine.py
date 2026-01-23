"""Unit tests for webhook command execution engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from core.webhook_engine import (
    execute_command,
    render_template,
    match_commands,
    action_create_task,
    action_comment,
    action_ask,
    action_respond
)
from core.database.models import WebhookCommandDB
class TestWebhookEngine:
    """Test webhook command execution engine."""
    
    async def test_execute_create_task_command(self):
        """Execute create_task command creates a task."""
        command = WebhookCommandDB(
            command_id="cmd-001",
            webhook_id="webhook-001",
            trigger="issues.opened",
            action="create_task",
            agent="planning",
            template="Issue: {{issue.title}}",
            priority=0
        )
        
        payload = {"issue": {"title": "Test Issue", "number": 123}}
        
        db_mock = AsyncMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        
        # Mock db.execute() to return a result object with scalar_one_or_none()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)  # No existing conversation
        db_mock.execute = AsyncMock(return_value=mock_result)
        
        with patch('core.webhook_engine.redis_client.push_task', new_callable=AsyncMock):
            result = await execute_command(command, payload, db_mock)
            
            assert result["action"] == "create_task"
            assert "task_id" in result
            assert result["agent"] == "planning"
    
    async def test_execute_comment_command(self):
        """Execute comment command posts comment (for dynamic webhooks)."""
        command = WebhookCommandDB(
            command_id="cmd-002",
            webhook_id="webhook-001",
            trigger="issues.opened",
            action="comment",
            template="Acknowledged: {{issue.number}}",
            priority=0
        )
        
        payload = {
            "issue": {"number": 123},
            "provider": "custom",
        }
        
        result = await execute_command(command, payload, None)
        
        assert result["action"] == "comment"
        assert result["status"] == "sent"
        assert result["provider"] == "custom"
    
    async def test_execute_ask_command(self):
        """Execute ask command creates interactive task."""
        command = WebhookCommandDB(
            command_id="cmd-003",
            webhook_id="webhook-001",
            trigger="issues.assigned",
            action="ask",
            agent="brain",
            template="Should I handle {{issue.title}}?",
            priority=0
        )
        
        payload = {"issue": {"title": "Test Issue", "number": 123}}
        
        db_mock = AsyncMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()
        db_mock.add = MagicMock()
        
        with patch('core.webhook_engine.redis_client.push_task', new_callable=AsyncMock):
            result = await execute_command(command, payload, db_mock)
            
            assert result["action"] == "ask"
            assert "task_id" in result
            assert result["interactive"] is True
    
    async def test_execute_respond_command(self):
        """Execute respond command sends immediate response."""
        command = WebhookCommandDB(
            command_id="cmd-004",
            webhook_id="webhook-001",
            trigger="test",
            action="respond",
            template="Processing {{event.type}}",
            priority=0
        )
        
        payload = {"event": {"type": "test_event"}}
        
        result = await execute_command(command, payload, None)
        
        assert result["action"] == "respond"
        assert result["status"] == "sent"


class TestTemplateRendering:
    """Test template rendering with payload data."""
    
    def test_render_simple_template(self):
        """Template rendering replaces variables."""
        template = "Issue #{{issue.number}}: {{issue.title}}"
        payload = {"issue": {"number": 123, "title": "Bug Report"}}
        
        rendered = render_template(template, payload)
        
        assert rendered == "Issue #123: Bug Report"
    
    def test_render_nested_template(self):
        """Template rendering handles nested objects."""
        template = "{{user.profile.name}} commented on {{issue.title}}"
        payload = {
            "user": {"profile": {"name": "John Doe"}},
            "issue": {"title": "Test Issue"}
        }
        
        rendered = render_template(template, payload)
        
        assert rendered == "John Doe commented on Test Issue"
    
    def test_render_missing_variable(self):
        """Template rendering handles missing variables gracefully."""
        template = "Issue: {{issue.title}} - {{issue.missing}}"
        payload = {"issue": {"title": "Test"}}
        
        rendered = render_template(template, payload)
        
        assert "Test" in rendered
        assert "{{issue.missing}}" in rendered or "missing" not in rendered
    
    def test_render_array_access(self):
        """Template rendering handles array access."""
        template = "First label: {{labels.0.name}}"
        payload = {"labels": [{"name": "bug"}, {"name": "urgent"}]}
        
        rendered = render_template(template, payload)
        
        assert "bug" in rendered


class TestCommandMatching:
    """Test command matching logic."""
    
    def test_match_exact_trigger(self):
        """Commands match exact trigger patterns."""
        commands = [
            WebhookCommandDB(
                command_id="cmd-001",
                webhook_id="webhook-001",
                trigger="issues.opened",
                action="create_task",
                template="test",
                priority=0
            ),
            WebhookCommandDB(
                command_id="cmd-002",
                webhook_id="webhook-001",
                trigger="pull_request.opened",
                action="create_task",
                template="test",
                priority=0
            )
        ]
        
        event_type = "issues.opened"
        payload = {"action": "opened"}
        
        matched = match_commands(commands, event_type, payload)
        
        assert len(matched) == 1
        assert matched[0].command_id == "cmd-001"
    
    def test_match_with_conditions(self):
        """Commands match with condition filtering."""
        commands = [
            WebhookCommandDB(
                command_id="cmd-001",
                webhook_id="webhook-001",
                trigger="issues.labeled",
                action="create_task",
                template="test",
                conditions_json='{"label": "urgent"}',
                priority=0
            )
        ]
        
        event_type = "issues.labeled"
        payload = {
            "action": "labeled",
            "label": {"name": "urgent"}
        }
        
        matched = match_commands(commands, event_type, payload)
        
        assert len(matched) == 1
    
    def test_match_conditions_not_met(self):
        """Commands don't match when conditions not met."""
        commands = [
            WebhookCommandDB(
                command_id="cmd-001",
                webhook_id="webhook-001",
                trigger="issues.labeled",
                action="create_task",
                template="test",
                conditions_json='{"label": "urgent"}',
                priority=0
            )
        ]
        
        event_type = "issues.labeled"
        payload = {
            "action": "labeled",
            "label": {"name": "bug"}
        }
        
        matched = match_commands(commands, event_type, payload)
        
        assert len(matched) == 0
    
    def test_match_priority_ordering(self):
        """Commands are ordered by priority."""
        commands = [
            WebhookCommandDB(
                command_id="cmd-001",
                webhook_id="webhook-001",
                trigger="issues.opened",
                action="create_task",
                template="test",
                priority=10
            ),
            WebhookCommandDB(
                command_id="cmd-002",
                webhook_id="webhook-001",
                trigger="issues.opened",
                action="create_task",
                template="test",
                priority=0
            )
        ]
        
        event_type = "issues.opened"
        payload = {"action": "opened"}
        
        matched = match_commands(commands, event_type, payload)
        
        assert len(matched) == 2
        assert matched[0].command_id == "cmd-002"
        assert matched[1].command_id == "cmd-001"
class TestActionHandlers:
    """Test individual action handlers."""
    
    async def test_action_create_task(self):
        """Create task action creates database entry and queues task."""
        db_mock = AsyncMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        
        # Mock db.execute() to return a result object with scalar_one_or_none()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)  # No existing conversation
        db_mock.execute = AsyncMock(return_value=mock_result)
        
        with patch('core.webhook_engine.redis_client.push_task', new_callable=AsyncMock):
            result = await action_create_task(
                agent="planning",
                message="Test task message",
                payload={"issue": {"number": 123}},
                db=db_mock
            )
            
            assert result["action"] == "create_task"
            assert "task_id" in result
            assert result["agent"] == "planning"
    
    async def test_action_comment_dynamic(self):
        """Comment action for dynamic webhooks."""
        payload = {
            "provider": "custom",
        }
        
        result = await action_comment(payload, "Test comment")
        
        assert result["action"] == "comment"
        assert result["status"] == "sent"
        assert result["provider"] == "custom"
    
    async def test_action_ask_creates_interactive_task(self):
        """Ask action creates interactive task."""
        db_mock = AsyncMock(spec=AsyncSession)
        db_mock.commit = AsyncMock()
        db_mock.add = MagicMock()
        
        with patch('core.webhook_engine.redis_client.push_task', new_callable=AsyncMock):
            result = await action_ask(
                agent="brain",
                message="Should I proceed?",
                payload={"issue": {"number": 123}},
                db=db_mock
            )
            
            assert result["action"] == "ask"
            assert "task_id" in result
            assert result["interactive"] is True
    
    async def test_action_respond(self):
        """Respond action sends immediate response."""
        payload = {"provider": "github"}
        
        result = await action_respond(payload, "Response message")
        
        assert result["action"] == "respond"
        assert result["status"] == "sent"
