"""TDD tests for GitHub completion handler."""

import pytest
from unittest.mock import AsyncMock, patch


class TestGitHubCompletionHandler:
    """Test GitHub task completion handler behavior."""
    
    @pytest.mark.asyncio
    async def test_posts_only_emoji_for_errors(self):
        """
        Business Rule: GitHub errors must post only emoji (❌), not full error message.
        Behavior: When success=False and error exists, only ❌ emoji is posted to GitHub.
        Full error details remain in logs and conversation.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.logger') as mock_logger:
            mock_post.return_value = True
            
            error_message = "Separator is not found, and chunk exceed the limit"
            
            await handle_github_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error=error_message,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="❌",
                success=False,
                cost_usd=0.0
            )
            
            mock_logger.info.assert_called()
            log_call = mock_logger.info.call_args
            assert log_call.args[0] == "github_task_error_posted"
            assert log_call.kwargs.get("task_id") == "task-123"
            assert error_message[:200] in log_call.kwargs.get("error_preview", "")
    
    @pytest.mark.asyncio
    async def test_passes_success_message_without_formatting(self):
        """
        Business Rule: Success messages are passed unchanged.
        Behavior: When success=True, message is passed as-is without emoji.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_github_task_completion(
                payload=payload,
                message="Task completed successfully",
                success=True,
                result="All checks passed",
                cost_usd=0.05,
                task_id="task-123"
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="Task completed successfully",
                success=True,
                cost_usd=0.05
            )
    
    @pytest.mark.asyncio
    async def test_calls_post_github_task_comment(self):
        """
        Business Rule: Handler must post comment to GitHub.
        Behavior: post_github_task_comment is called with formatted message.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "pull_request": {"number": 456}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Review complete",
                success=True,
                cost_usd=0.1,
                task_id="task-456",
                command="review pr"
            )
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calls_send_slack_notification(self):
        """
        Business Rule: Handler must send Slack notification.
        Behavior: send_slack_notification is called with task details.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 789}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_github_task_completion(
                payload=payload,
                message="Task done",
                success=True,
                result="Output here",
                error=None,
                cost_usd=0.05,
                task_id="task-789",
                command="analyze code"
            )
            
            mock_slack.assert_called_once_with(
                task_id="task-789",
                webhook_source="github",
                command="analyze code",
                success=True,
                result="Output here",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_returns_false_when_comment_post_fails(self):
        """
        Business Rule: Handler must return False when comment posting fails.
        Behavior: Returns False when post_github_task_comment returns False.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 999}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Test",
                success=True,
                cost_usd=0.0
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_posts_only_emoji_when_error_exists_even_with_message(self):
        """
        Business Rule: When error exists, always post only emoji regardless of message.
        Behavior: If error parameter exists, only ❌ is posted, message is ignored for GitHub.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 111}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_github_task_completion(
                payload=payload,
                message="Task failed with details",
                success=False,
                error="Actual error message",
                cost_usd=0.0
            )
            
            mock_post.assert_called_once_with(
                payload=payload,
                message="❌",
                success=False,
                cost_usd=0.0
            )
    
    @pytest.mark.asyncio
    async def test_handles_missing_error_gracefully(self):
        """
        Business Rule: Handler must handle missing error parameter gracefully.
        Behavior: When success=False but error=None, uses message as-is (for backward compatibility).
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 111}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            await handle_github_task_completion(
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
