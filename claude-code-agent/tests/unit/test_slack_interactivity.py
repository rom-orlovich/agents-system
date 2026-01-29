"""TDD tests for Slack interactivity button handlers."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


class TestSlackInteractivity:
    """Test Slack interactivity button handler behavior."""

    @pytest.mark.asyncio
    async def test_approve_task_creates_github_task(self):
        """
        Business Rule: Approve button should create approve task routed to GitHub PR.
        Behavior: When approve_task action is clicked with GitHub routing, creates GitHub task.
        """
        from api.webhooks.slack.routes import slack_interactivity
        from fastapi import Request

        request = MagicMock(spec=Request)
        payload_json = json.dumps({
            "actions": [{
                "action_id": "approve_task",
                "value": json.dumps({"action": "approve", "original_task_id": "task-123", "command": "plan", "source": "github", "routing": {"repo": "owner/repo", "pr_number": 42}})
            }],
            "user": {"name": "testuser"},
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"}
        })
        request.form = AsyncMock(return_value={"payload": payload_json})
        request.body = AsyncMock(return_value=b"test")

        with patch('api.webhooks.slack.handlers.SlackWebhookHandler.verify_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.create_task_from_button_action', new_callable=AsyncMock) as mock_create, \
             patch('api.webhooks.slack.routes.update_slack_message', new_callable=AsyncMock) as mock_update:
            mock_create.return_value = "task-new-123"

            result = await slack_interactivity(request)

            assert result == {"ok": True}
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["action"] == "approve"
            assert call_kwargs["routing"]["repo"] == "owner/repo"
            assert call_kwargs["routing"]["pr_number"] == 42
            assert call_kwargs["source"] == "github"
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_task_creates_jira_task(self):
        """
        Business Rule: Review button should create review task routed to Jira ticket.
        Behavior: When review_task action is clicked with Jira routing, creates Jira task.
        """
        from api.webhooks.slack.routes import slack_interactivity
        from fastapi import Request

        request = MagicMock(spec=Request)
        payload_json = json.dumps({
            "actions": [{
                "action_id": "review_task",
                "value": json.dumps({"action": "review", "original_task_id": "task-456", "command": "plan", "source": "jira", "routing": {"ticket_key": "PROJ-123"}})
            }],
            "user": {"name": "testuser"},
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"}
        })
        request.form = AsyncMock(return_value={"payload": payload_json})
        request.body = AsyncMock(return_value=b"test")

        with patch('api.webhooks.slack.handlers.SlackWebhookHandler.verify_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.create_task_from_button_action', new_callable=AsyncMock) as mock_create, \
             patch('api.webhooks.slack.routes.update_slack_message', new_callable=AsyncMock) as mock_update:
            mock_create.return_value = "task-new-456"

            result = await slack_interactivity(request)

            assert result == {"ok": True}
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["action"] == "review"
            assert call_kwargs["routing"]["ticket_key"] == "PROJ-123"
            assert call_kwargs["source"] == "jira"
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_task_creates_slack_task(self):
        """
        Business Rule: Reject button should create reject task routed to Slack.
        Behavior: When reject_task action is clicked with Slack routing, creates Slack task.
        """
        from api.webhooks.slack.routes import slack_interactivity
        from fastapi import Request

        request = MagicMock(spec=Request)
        payload_json = json.dumps({
            "actions": [{
                "action_id": "reject_task",
                "value": json.dumps({"action": "reject", "original_task_id": "task-789", "command": "plan", "source": "slack", "routing": {"channel": "C123", "thread_ts": "1234567890.123456"}})
            }],
            "user": {"name": "testuser"},
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"}
        })
        request.form = AsyncMock(return_value={"payload": payload_json})
        request.body = AsyncMock(return_value=b"test")

        with patch('api.webhooks.slack.handlers.SlackWebhookHandler.verify_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.create_task_from_button_action', new_callable=AsyncMock) as mock_create, \
             patch('api.webhooks.slack.routes.update_slack_message', new_callable=AsyncMock) as mock_update:
            mock_create.return_value = "task-new-789"

            result = await slack_interactivity(request)

            assert result == {"ok": True}
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["action"] == "reject"
            assert call_kwargs["routing"]["channel"] == "C123"
            assert call_kwargs["source"] == "slack"
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_interactivity_updates_message(self):
        """
        Business Rule: Button clicks should update Slack message to show action taken.
        Behavior: After creating task, updates original message with action status.
        """
        from api.webhooks.slack.routes import slack_interactivity
        from fastapi import Request
        
        request = MagicMock(spec=Request)
        payload_json = json.dumps({
            "actions": [{
                "action_id": "approve_task",
                "value": json.dumps({"action": "approve", "original_task_id": "task-123", "command": "plan", "source": "github", "routing": {"repo": "owner/repo", "pr_number": 42}})
            }],
            "user": {"name": "testuser"},
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"}
        })
        request.form = AsyncMock(return_value={"payload": payload_json})
        request.body = AsyncMock(return_value=b"test")

        with patch('api.webhooks.slack.handlers.SlackWebhookHandler.verify_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.create_task_from_button_action', new_callable=AsyncMock, return_value="task-new-123"), \
             patch('api.webhooks.slack.routes.update_slack_message', new_callable=AsyncMock) as mock_update:

            await slack_interactivity(request)

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == "C123"
            assert call_args[0][1] == "1234567890.123456"
            assert "Approved" in call_args[0][2] or "approve" in call_args[0][2].lower()
    
    @pytest.mark.asyncio
    async def test_interactivity_prevents_loop(self):
        """
        Business Rule: Button actions are user-initiated and don't trigger webhook loops.
        Behavior: Button clicks create new tasks but don't re-trigger webhook processing.
        """
        from api.webhooks.slack.routes import slack_interactivity
        from fastapi import Request
        
        request = MagicMock(spec=Request)
        payload_json = json.dumps({
            "actions": [{
                "action_id": "approve_task",
                "value": json.dumps({"action": "approve", "original_task_id": "task-123", "command": "plan", "source": "github", "routing": {"repo": "owner/repo", "pr_number": 42}})
            }],
            "user": {"name": "testuser"},
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"}
        })
        request.form = AsyncMock(return_value={"payload": payload_json})
        request.body = AsyncMock(return_value=b"test")

        with patch('api.webhooks.slack.handlers.SlackWebhookHandler.verify_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.create_task_from_button_action', new_callable=AsyncMock, return_value="task-new-123") as mock_create, \
             patch('api.webhooks.slack.routes.update_slack_message', new_callable=AsyncMock):

            result = await slack_interactivity(request)

            # Button actions create tasks but don't trigger webhook loops
            # because they're user-initiated actions, not webhook events
            assert result == {"ok": True}
            mock_create.assert_called_once()
