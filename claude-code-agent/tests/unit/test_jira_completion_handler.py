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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = (True, {"id": 123})
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error="Something went wrong",
                cost_usd=0.0,
                task_id="task-123"
            )
            
            mock_post.assert_called_once()
    
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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = (True, {"id": 123})
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task completed successfully",
                success=True,
                result="Analysis complete",
                cost_usd=0.05,
                task_id="task-456"
            )
            
            mock_post.assert_called_once()
    
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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = (True, {"id": 123})
            
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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock, return_value=(True, {"id": 123})), \
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
            
            mock_slack.assert_called_once()
            call_kwargs = mock_slack.call_args[1]
            assert call_kwargs["task_id"] == "task-999"
            assert call_kwargs["webhook_source"] == "jira"
            assert call_kwargs["command"] == "review ticket"
            assert call_kwargs["success"] is True
            assert call_kwargs["result"] == "Output here"
            assert call_kwargs["error"] is None
    
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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock, return_value=(False, None)), \
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
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = (True, {"id": 123})
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task failed",
                success=False,
                error=None,
                cost_usd=0.0
            )
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extracts_pr_url_from_result(self):
        """Test that PR URL is extracted from result and passed to post_jira_task_comment."""
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-333", "fields": {"summary": "Test"}}
        }
        
        result_with_pr = "Task completed. PR: https://github.com/owner/repo/pull/123"
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = (True, {"id": 123})
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task completed",
                success=True,
                result=result_with_pr,
                cost_usd=0.05,
                task_id="task-333"
            )
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_passes_pr_url_to_slack_notification(self):
        """Test that PR URL is passed to Slack notification."""
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "TEST-444", "fields": {"summary": "Test"}}
        }
        
        result_with_pr = "PR created: https://github.com/test/repo/pull/456"
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock, return_value=(True, {"id": 123})), \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task done",
                success=True,
                result=result_with_pr,
                cost_usd=0.1,
                task_id="task-444"
            )
            
            mock_slack.assert_called_once()
            call_kwargs = mock_slack.call_args[1]
            assert call_kwargs["pr_url"] == "https://github.com/test/repo/pull/456"
    
    @pytest.mark.asyncio
    async def test_extracts_user_request_from_comment(self):
        """Test that user request is extracted from comment body and passed to Slack notification."""
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {"key": "KAN-5", "fields": {"summary": "Test issue"}},
            "comment": {
                "body": "@agent analyze Sentry error JAVASCRIPT-REACT-3",
                "author": {"displayName": "testuser"}
            },
            "_user_content": "analyze Sentry error JAVASCRIPT-REACT-3"
        }
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock, return_value=(True, {"id": 123})), \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_jira_task_completion(
                payload=payload,
                message="Analysis complete",
                success=True,
                result="Analysis done",
                cost_usd=0.05,
                task_id="task-555",
                command="analyze"
            )
            
            mock_slack.assert_called_once()
            call_kwargs = mock_slack.call_args[1]
            assert call_kwargs["user_request"] == "analyze Sentry error JAVASCRIPT-REACT-3"
            assert call_kwargs["ticket_key"] == "KAN-5"
    
    @pytest.mark.asyncio
    async def test_extracts_user_request_from_issue_description(self):
        """Test that user request is extracted from issue description when no comment."""
        from api.webhooks.jira.routes import handle_jira_task_completion
        
        payload = {
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Fix bug",
                    "description": "Please analyze this issue"
                }
            }
        }
        
        with patch('api.webhooks.jira.handlers.JiraResponseHandler.post_response', new_callable=AsyncMock, return_value=(True, {"id": 123})), \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            await handle_jira_task_completion(
                payload=payload,
                message="Task done",
                success=True,
                cost_usd=0.1,
                task_id="task-666"
            )
            
            mock_slack.assert_called_once()
            call_kwargs = mock_slack.call_args[1]
            assert call_kwargs["ticket_key"] == "PROJ-123"
            assert "user_request" in call_kwargs
    
    @pytest.mark.asyncio
    async def test_slack_notification_includes_user_request_and_ticket_key(self):
        """Test that Slack notification includes user request and ticket key in blocks."""
        from api.webhooks.jira.utils import send_slack_notification
        
        with patch('core.slack_client.slack_client') as mock_slack_client:
            mock_slack_client.post_message = AsyncMock(return_value={"ok": True})
            
            result_text = """## Summary
Analysis complete.

## What Was Done
- Analyzed error
- Posted to Jira"""
            
            await send_slack_notification(
                task_id="task-777",
                webhook_source="jira",
                command="analyze",
                success=True,
                result=result_text,
                user_request="analyze Sentry error",
                ticket_key="KAN-5",
                cost_usd=0.05
            )
            
            mock_slack_client.post_message.assert_called_once()
            call_kwargs = mock_slack_client.post_message.call_args[1]
            blocks = call_kwargs["blocks"]
            
            blocks_text = " ".join([str(b.get("text", {}).get("text", "")) for b in blocks if b.get("text")])
            blocks_str = str(blocks)
            assert "KAN-5" in blocks_text or "KAN-5" in blocks_str
            assert "analyze Sentry error" in blocks_text or "analyze Sentry error" in blocks_str