"""TDD tests for Jira infinite loop prevention."""

import pytest
from unittest.mock import AsyncMock, patch


class TestJiraLoopPrevention:
    """Test Jira infinite loop prevention mechanisms."""
    
    @pytest.mark.asyncio
    async def test_jira_skips_own_posted_comment(self):
        """
        Business Rule: Agent must skip processing comments it posted.
        Behavior: is_agent_posted_jira_comment() returns True for tracked comment_id.
        """
        from api.webhooks.jira.utils import is_agent_posted_jira_comment
        
        comment_id = "12345"
        
        with patch('api.webhooks.jira.utils.redis_client.exists', new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = True
            
            result = await is_agent_posted_jira_comment(comment_id)
            
            assert result is True
            mock_exists.assert_called_once_with(f"jira:posted_comment:{comment_id}")
    
    @pytest.mark.asyncio
    async def test_jira_allows_untracked_comment(self):
        """
        Business Rule: Agent must process comments it didn't post.
        Behavior: is_agent_posted_jira_comment() returns False for untracked comment_id.
        """
        from api.webhooks.jira.utils import is_agent_posted_jira_comment
        
        comment_id = "12345"
        
        with patch('api.webhooks.jira.utils.redis_client.exists', new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = False
            
            result = await is_agent_posted_jira_comment(comment_id)
            
            assert result is False
            mock_exists.assert_called_once_with(f"jira:posted_comment:{comment_id}")
    
    @pytest.mark.asyncio
    async def test_jira_tracks_posted_comment(self):
        """
        Business Rule: Agent must track comments it posts to prevent loops.
        Behavior: Jira comment posting functions store comment_id in Redis after posting.
        """
        # This test will verify the tracking happens in post_jira_comment
        # For now, we verify the function exists
        from api.webhooks.jira.utils import post_jira_comment
        assert callable(post_jira_comment)
    
    @pytest.mark.asyncio
    async def test_jira_checks_own_account(self):
        """
        Business Rule: Agent must skip comments from its own Jira account.
        Behavior: is_agent_own_jira_account() returns True when account_id matches configured account.
        """
        from api.webhooks.jira.utils import is_agent_own_jira_account
        
        account_id = "557058:abc123def456"
        
        with patch('api.webhooks.jira.utils.settings.jira_account_id', account_id):
            result = await is_agent_own_jira_account(account_id)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_jira_allows_different_account(self):
        """
        Business Rule: Agent must process comments from other Jira accounts.
        Behavior: is_agent_own_jira_account() returns False when account_id doesn't match.
        """
        from api.webhooks.jira.utils import is_agent_own_jira_account
        
        configured_account_id = "557058:abc123def456"
        different_account_id = "557058:xyz789ghi012"
        
        with patch('api.webhooks.jira.utils.settings.jira_account_id', configured_account_id):
            result = await is_agent_own_jira_account(different_account_id)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_jira_match_command_skips_tracked_comment(self):
        """
        Business Rule: match_jira_command() must skip comments posted by agent.
        Behavior: Returns None when comment_id is tracked in Redis.
        """
        from api.webhooks.jira.utils import match_jira_command
        
        payload = {
            "comment": {
                "id": "12345",
                "body": "@agent analyze",
                "author": {
                    "accountId": "557058:abc123",
                    "displayName": "Test User",
                    "accountType": "atlassian"
                }
            },
            "issue": {
                "key": "PROJ-123"
            }
        }
        
        with patch('api.webhooks.jira.utils.is_agent_posted_jira_comment', new_callable=AsyncMock) as mock_check, \
             patch('api.webhooks.jira.utils.is_agent_own_jira_account', new_callable=AsyncMock, return_value=False):
            mock_check.return_value = True
            
            result = await match_jira_command(payload, "comment_created")
            
            assert result is None
            mock_check.assert_called_once_with("12345")
    
    @pytest.mark.asyncio
    async def test_jira_match_command_skips_own_account(self):
        """
        Business Rule: match_jira_command() must skip comments from agent's own account.
        Behavior: Returns None when account_id matches configured Jira account ID.
        """
        from api.webhooks.jira.utils import match_jira_command
        
        payload = {
            "comment": {
                "id": "12345",
                "body": "@agent analyze",
                "author": {
                    "accountId": "557058:abc123def456",
                    "displayName": "AI Agent",
                    "accountType": "atlassian"
                }
            },
            "issue": {
                "key": "PROJ-123"
            }
        }
        
        with patch('api.webhooks.jira.utils.is_agent_posted_jira_comment', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.jira.utils.is_agent_own_jira_account', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            result = await match_jira_command(payload, "comment_created")
            
            assert result is None
            mock_check.assert_called_once_with("557058:abc123def456")
