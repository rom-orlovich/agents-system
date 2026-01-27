"""TDD tests for Slack completion handler."""

import pytest
from unittest.mock import AsyncMock, patch


class TestSlackCompletionHandler:
    """Test Slack task completion handler behavior."""
    
    @pytest.mark.asyncio
    async def test_formats_error_message_cleanly_without_emoji(self):
        """
        Business Rule: Slack errors must be formatted cleanly without emoji.
        Behavior: Error messages use error text directly when success=False and error exists.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C123",
                "text": "@agent help",
                "user": "U123",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.slack.utils.extract_task_summary') as mock_extract, \
             patch('api.webhooks.slack.utils.build_task_completion_blocks') as mock_build:
            mock_post.return_value = True
            mock_extract.return_value = {"summary": "Task failed", "classification": "SIMPLE"}
            mock_build.return_value = [{"type": "header", "text": {"type": "plain_text", "text": "✅ Task Completed - SIMPLE"}}]
            
            await handle_slack_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Something went wrong",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs["payload"] == payload
            assert call_args.kwargs["message"] == "Something went wrong"
            assert call_args.kwargs["success"] is False
            assert call_args.kwargs["cost_usd"] == 0.0
            assert "blocks" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_passes_success_message_without_formatting(self):
        """
        Business Rule: Success messages are passed unchanged.
        Behavior: When success=True, message is passed as-is.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C456",
                "text": "@agent analyze",
                "user": "U456",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.slack.utils.extract_task_summary') as mock_extract, \
             patch('api.webhooks.slack.utils.build_task_completion_blocks') as mock_build:
            mock_post.return_value = True
            mock_extract.return_value = {"summary": "Analysis complete", "classification": "SIMPLE"}
            mock_build.return_value = [{"type": "header", "text": {"type": "plain_text", "text": "✅ Task Completed - SIMPLE"}}]
            
            await handle_slack_task_completion(
                payload=payload,
                message="Task completed successfully",
                success=True,
                result="Analysis complete",
                cost_usd=0.05,
                task_id="task-456"
            )
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs["payload"] == payload
            assert call_args.kwargs["message"] == "Task completed successfully"
            assert call_args.kwargs["success"] is True
            assert call_args.kwargs["cost_usd"] == 0.05
            assert "blocks" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_calls_post_slack_task_comment(self):
        """
        Business Rule: Handler must post message to Slack thread.
        Behavior: post_slack_task_comment is called with formatted message.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C789",
                "text": "@agent review",
                "user": "U789",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await handle_slack_task_completion(
                payload=payload,
                message="Review complete",
                success=True,
                cost_usd=0.1,
                task_id="task-789",
                command="review code"
            )
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calls_send_slack_notification(self):
        """
        Business Rule: Handler must send Slack notification.
        Behavior: send_slack_notification is called with task details.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C999",
                "text": "@agent help",
                "user": "U999",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_slack_task_completion(
                payload=payload,
                message="Task done",
                success=True,
                result="Output here",
                error=None,
                cost_usd=0.05,
                task_id="task-999",
                command="help"
            )
            
            mock_slack.assert_called_once_with(
                task_id="task-999",
                webhook_source="slack",
                command="help",
                success=True,
                result="Output here",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_returns_false_when_message_post_fails(self):
        """
        Business Rule: Handler must return False when message posting fails.
        Behavior: Returns False when post_slack_task_comment returns False.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C111",
                "text": "@agent test",
                "user": "U111",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock):
            
            result = await handle_slack_task_completion(
                payload=payload,
                message="Test",
                success=True,
                cost_usd=0.0
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_handles_missing_error_gracefully(self):
        """
        Business Rule: Handler must handle missing error parameter gracefully.
        Behavior: When success=False but error=None, uses message as-is.
        """
        from api.webhooks.slack.routes import handle_slack_task_completion
        
        payload = {
            "event": {
                "channel": "C222",
                "text": "@agent test",
                "user": "U222",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.slack.utils.extract_task_summary') as mock_extract, \
             patch('api.webhooks.slack.utils.build_task_completion_blocks') as mock_build:
            mock_post.return_value = True
            mock_extract.return_value = {"summary": "Task failed", "classification": "SIMPLE"}
            mock_build.return_value = [{"type": "header", "text": {"type": "plain_text", "text": "✅ Task Completed - SIMPLE"}}]
            
            await handle_slack_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error=None,
                cost_usd=0.0
            )
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs["payload"] == payload
            assert call_args.kwargs["message"] == "Task failed"
            assert call_args.kwargs["success"] is False
            assert call_args.kwargs["cost_usd"] == 0.0
            assert "blocks" in call_args.kwargs
