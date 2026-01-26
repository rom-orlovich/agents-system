"""TDD tests for Jira completion handler."""

import pytest
from unittest.mock import AsyncMock, patch


class TestJiraCompletionHandler:
    """Test Jira task completion handler behavior."""
    
    @pytest.mark.asyncio
    async def test_formats_error_message_cleanly_without_emoji(self):
        """
        Business Rule: Jira errors must be formatted cleanly without emoji.
        Behavior: Error messages use error text directly when success=False and error exists.
        """
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-123", "fields": {"summary": "Test issue"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Something went wrong",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="Something went wrong",
                success=False,
                cost_usd=0.0
            )
    
    @pytest.mark.asyncio
    async def test_passes_success_message_without_formatting(self):
        """
        Business Rule: Success messages are passed unchanged.
        Behavior: When success=True, message is passed as-is.
        """
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-456", "fields": {"summary": "Test issue"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task completed successfully",
                success=True,
                result="Analysis complete",
                cost_usd=0.05,
                task_id="task-456"
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="Task completed successfully",
                success=True,
                cost_usd=0.05
            )
    
    @pytest.mark.asyncio
    async def test_calls_post_jira_task_comment(self):
        """
        Business Rule: Handler must post comment to Jira.
        Behavior: post_jira_task_comment is called with formatted message.
        """
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "PROJ-789", "fields": {"summary": "Test"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await handle_jira_task_completion(
                payload=payload,
                message="Analysis complete",
                success=True,
                cost_usd=0.1,
                task_id="task-789",
                command="analyze ticket"
            )
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calls_send_slack_notification(self):
        """
        Business Rule: Handler must send Slack notification.
        Behavior: send_slack_notification is called with task details.
        """
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-999", "fields": {"summary": "Test"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task done",
                success=True,
                result="Output here",
                error=None,
                cost_usd=0.05,
                task_id="task-999",
                command="review ticket"
            )
            
            mock_slack.assert_called_once_with(
                task_id="task-999",
                webhook_source="jira",
                command="review ticket",
                success=True,
                result="Output here",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_returns_false_when_comment_post_fails(self):
        """
        Business Rule: Handler must return False when comment posting fails.
        Behavior: Returns False when post_jira_task_comment returns False.
        """
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-111", "fields": {"summary": "Test"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            
            result = await handle_jira_task_completion(
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
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-222", "fields": {"summary": "Test"}}
        }
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error=None,
                cost_usd=0.0
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="Task failed",
                success=False,
                cost_usd=0.0
            )
