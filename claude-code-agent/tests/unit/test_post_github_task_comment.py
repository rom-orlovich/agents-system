"""TDD tests for post_github_task_comment function."""

import pytest
from unittest.mock import AsyncMock, patch


class TestPostGitHubTaskComment:
    """Test post_github_task_comment behavior."""
    
    @pytest.mark.asyncio
    async def test_posts_emoji_only_for_errors(self):
        """
        Business Rule: Error comments post only emoji (❌) to GitHub.
        Behavior: When success=False, only ❌ emoji is posted, not full error message.
        """
        from api.webhooks.github.utils import post_github_task_comment
        from core.github_client import github_client
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 123}
        }
        
        with patch.object(github_client, 'post_issue_comment', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": 1}
            
            result = await post_github_task_comment(
                payload=payload,
                message="❌",
                success=False,
                cost_usd=0.0
            )
            
            assert result is True
            mock_post.assert_called_once_with("test", "repo", 123, "❌")
    
    @pytest.mark.asyncio
    async def test_posts_full_message_for_success(self):
        """
        Business Rule: Success comments post full message with ✅ emoji.
        Behavior: When success=True, full message with ✅ is posted.
        """
        from api.webhooks.github.utils import post_github_task_comment
        from core.github_client import github_client
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "pull_request": {"number": 456}
        }
        
        with patch.object(github_client, 'post_pr_comment', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": 1}
            
            result = await post_github_task_comment(
                payload=payload,
                message="Task completed successfully",
                success=True,
                cost_usd=0.05
            )
            
            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][2] == 456
            assert "✅ Task completed successfully" in call_args[0][3]
            assert "💰 Cost: $0.05" in call_args[0][3]
    
    @pytest.mark.asyncio
    async def test_handles_emoji_only_message(self):
        """
        Business Rule: Emoji-only messages should be posted as-is.
        Behavior: When message is just "❌", it's posted without modification.
        """
        from api.webhooks.github.utils import post_github_task_comment
        from core.github_client import github_client
        
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 789}
        }
        
        with patch.object(github_client, 'post_issue_comment', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": 1}
            
            result = await post_github_task_comment(
                payload=payload,
                message="❌",
                success=False,
                cost_usd=0.0
            )
            
            assert result is True
            mock_post.assert_called_once_with("test", "repo", 789, "❌")
