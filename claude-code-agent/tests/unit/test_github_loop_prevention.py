"""TDD tests for GitHub PR review comment loop prevention."""

import pytest
from unittest.mock import AsyncMock, patch


class TestGitHubPRReviewCommentLoopPrevention:
    """Test GitHub PR review comment infinite loop prevention."""
    
    @pytest.mark.asyncio
    async def test_github_pr_review_comment_tracked(self):
        """
        Business Rule: Agent must track PR review comments it posts.
        Behavior: PR review comment IDs are stored in Redis after posting.
        """
        from api.webhooks.github.utils import post_github_task_comment
        
        payload = {
            "repository": {
                "owner": {"login": "owner"},
                "name": "repo"
            },
            "pull_request": {
                "number": 42
            }
        }
        
        mock_response = {"id": 12345}
        
        with patch('api.webhooks.github.utils.github_client.post_pr_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.utils.redis_client._client') as mock_redis:
            mock_post.return_value = mock_response
            
            await post_github_task_comment(
                payload=payload,
                message="Test comment",
                success=True,
                cost_usd=0.0
            )
            
            # Verify Redis tracking was called
            mock_redis.setex.assert_called_once_with(
                "github:posted_comment:12345",
                3600,
                "1"
            )
    
    @pytest.mark.asyncio
    async def test_github_skips_tracked_pr_review_comment(self):
        """
        Business Rule: Agent must skip PR review comments it posted.
        Behavior: is_agent_posted_comment() returns True for tracked PR review comment IDs.
        """
        from api.webhooks.github.utils import is_agent_posted_comment
        
        comment_id = 12345
        
        with patch('api.webhooks.github.utils.redis_client.exists', new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = True
            
            result = await is_agent_posted_comment(comment_id)
            
            assert result is True
            mock_exists.assert_called_once_with(f"github:posted_comment:{comment_id}")
    
    @pytest.mark.asyncio
    async def test_github_match_command_checks_pr_review_comment(self):
        """
        Business Rule: match_github_command() must check PR review comments.
        Behavior: Returns None when PR review comment ID is tracked in Redis.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "created",
            "comment": {
                "id": 12345,
                "body": "@agent review",
                "pull_request_review_id": 67890
            },
            "repository": {
                "owner": {"login": "owner"},
                "name": "repo"
            },
            "pull_request": {
                "number": 42
            },
            "sender": {
                "login": "testuser",
                "type": "User"
            }
        }
        
        with patch('core.command_matcher.is_bot_comment', return_value=False), \
             patch('api.webhooks.github.utils.is_agent_posted_comment', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            result = await match_github_command(payload, "pull_request_review_comment.created")
            
            assert result is None
            mock_check.assert_called_once_with(12345)
