"""TDD tests for GitHub completion handler."""

import pytest
from unittest.mock import AsyncMock, patch


class TestGitHubCompletionHandler:
    """Test GitHub task completion handler behavior."""
    
    @pytest.mark.asyncio
    async def test_no_new_comment_for_errors_only_reaction(self):
        """
        Business Rule: GitHub errors should NOT post new comment, only add reaction to original comment.
        Behavior: When success=False and error exists, no new comment is posted to GitHub.
        Only reaction is added to original comment, error details sent to Slack only.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"), \
             patch('api.webhooks.github.routes.logger') as mock_logger:
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            error_message = "Separator is not found, and chunk exceed the limit"
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error=error_message,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False
            
            mock_github_client.add_reaction.assert_called_once_with(
                "test",
                "repo",
                12345,
                reaction="-1"
            )
    
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
    async def test_no_new_comment_when_error_exists_even_with_message(self):
        """
        Business Rule: When error exists, do NOT post new comment, only add reaction.
        Behavior: If error parameter exists, no new comment is posted, only reaction on original comment.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 11111},
            "issue": {"number": 111}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"):
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Task failed with details",
                success=False,
                error="Actual error message",
                cost_usd=0.0
            )
            
            mock_post.assert_not_called()
            assert result is False
    
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

    @pytest.mark.asyncio
    async def test_adds_reaction_to_original_comment_on_error(self):
        """
        Business Rule: Always add reaction to original comment when task fails.
        Behavior: When success=False and error exists, add "-1" reaction to original comment.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"):
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            await handle_github_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Some error occurred",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_github_client.add_reaction.assert_called_once_with(
                "test",
                "repo",
                12345,
                reaction="-1"
            )

    @pytest.mark.asyncio
    async def test_skips_new_comment_when_meaningful_response_exists(self):
        """
        Business Rule: If meaningful response already posted, don't post new error comment.
        Behavior: When has_meaningful_response=True and error exists, skip posting new comment to GitHub.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        meaningful_result = "This is a comprehensive review with detailed analysis and recommendations for improvement."
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"), \
             patch('api.webhooks.github.routes.logger') as mock_logger:
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Review completed",
                success=False,
                error="Task failed after posting review",
                result=meaningful_result,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False
            
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert "github_task_failed_but_response_already_posted" in log_calls

    @pytest.mark.asyncio
    async def test_no_new_comment_even_when_no_meaningful_response(self):
        """
        Business Rule: Never post new comment for errors, only reaction.
        Behavior: When has_meaningful_response=False and error exists, still no new comment posted.
        Only reaction is added to original comment.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"):
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message="❌",
                success=False,
                error="Task failed",
                result=None,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False
            
            mock_github_client.add_reaction.assert_called_once_with(
                "test",
                "repo",
                12345,
                reaction="-1"
            )

    @pytest.mark.asyncio
    async def test_handles_missing_comment_id_gracefully(self):
        """
        Business Rule: Handler must handle missing comment ID gracefully.
        Behavior: When comment ID is missing, skip reaction and don't post new comment.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client:
            
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Some error",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_github_client.add_reaction.assert_not_called()
            mock_post.assert_not_called()
            assert result is False

    @pytest.mark.asyncio
    async def test_handles_reaction_failure_gracefully(self):
        """
        Business Rule: Handler must continue even if reaction fails.
        Behavior: When reaction addition fails, still don't post new comment.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"), \
             patch('api.webhooks.github.routes.logger') as mock_logger:
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock(side_effect=Exception("Reaction failed"))
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Some error",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False
            
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("github_error_reaction_failed" in str(call) for call in warning_calls)

    @pytest.mark.asyncio
    async def test_detects_meaningful_response_from_result(self):
        """
        Business Rule: Detect meaningful response from result field.
        Behavior: If result has >50 characters, it's considered meaningful.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        long_result = "A" * 100
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"):
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message="Short",
                success=False,
                error="Error",
                result=long_result,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False

    @pytest.mark.asyncio
    async def test_detects_meaningful_response_from_message(self):
        """
        Business Rule: Detect meaningful response from message field.
        Behavior: If message has >50 characters and is not just "❌", it's considered meaningful.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "comment": {"id": 12345},
            "issue": {"number": 123}
        }
        
        long_message = "This is a comprehensive review with detailed analysis and recommendations."
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('core.github_client.github_client') as mock_github_client, \
             patch('os.getenv', return_value="test-token"):
            
            mock_github_client.token = "test-token"
            mock_github_client.headers = {}
            mock_github_client.add_reaction = AsyncMock()
            
            result = await handle_github_task_completion(
                payload=payload,
                message=long_message,
                success=False,
                error="Error",
                result=None,
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_not_called()
            assert result is False
