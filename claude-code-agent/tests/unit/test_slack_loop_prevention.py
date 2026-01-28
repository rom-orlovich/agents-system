"""TDD tests for Slack infinite loop prevention."""

import pytest
from unittest.mock import AsyncMock, patch


class TestSlackLoopPrevention:
    """Test Slack infinite loop prevention mechanisms."""
    
    @pytest.mark.asyncio
    async def test_slack_skips_own_posted_message(self):
        """
        Business Rule: Agent must skip processing messages it posted.
        Behavior: is_agent_posted_slack_message() returns True for tracked message_ts.
        """
        from api.webhooks.slack.utils import is_agent_posted_slack_message
        
        message_ts = "1234567890.123456"
        
        with patch('api.webhooks.slack.utils.redis_client.exists', new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = True
            
            result = await is_agent_posted_slack_message(message_ts)
            
            assert result is True
            mock_exists.assert_called_once_with(f"slack:posted_message:{message_ts}")
    
    @pytest.mark.asyncio
    async def test_slack_allows_untracked_message(self):
        """
        Business Rule: Agent must process messages it didn't post.
        Behavior: is_agent_posted_slack_message() returns False for untracked message_ts.
        """
        from api.webhooks.slack.utils import is_agent_posted_slack_message
        
        message_ts = "1234567890.123456"
        
        with patch('api.webhooks.slack.utils.redis_client.exists', new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = False
            
            result = await is_agent_posted_slack_message(message_ts)
            
            assert result is False
            mock_exists.assert_called_once_with(f"slack:posted_message:{message_ts}")
    
    @pytest.mark.asyncio
    async def test_slack_tracks_posted_message(self):
        """
        Business Rule: Agent must track messages it posts to prevent loops.
        Behavior: post_slack_task_comment() stores message_ts in Redis after posting.
        """
        from api.webhooks.slack.utils import post_slack_task_comment
        
        payload = {
            "event": {
                "channel": "C123",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.utils.slack_client.post_message', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.utils.redis_client._client') as mock_redis:
            mock_post.return_value = {"ts": "1234567890.123456", "ok": True}
            
            await post_slack_task_comment(
                payload=payload,
                message="Test message",
                success=True,
                cost_usd=0.0
            )
            
            # Verify Redis tracking was called
            mock_redis.setex.assert_called_once_with(
                "slack:posted_message:1234567890.123456",
                3600,
                "1"
            )
    
    @pytest.mark.asyncio
    async def test_slack_checks_own_app_id(self):
        """
        Business Rule: Agent must skip messages from its own Slack app.
        Behavior: is_agent_own_slack_app() returns True when app_id matches configured app.
        """
        from api.webhooks.slack.utils import is_agent_own_slack_app
        
        app_id = "A123456"
        bot_id = "B789012"
        
        with patch('api.webhooks.slack.utils.settings.slack_app_id', app_id):
            result = await is_agent_own_slack_app(app_id, bot_id)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_slack_allows_different_app_id(self):
        """
        Business Rule: Agent must process messages from other Slack apps.
        Behavior: is_agent_own_slack_app() returns False when app_id doesn't match.
        """
        from api.webhooks.slack.utils import is_agent_own_slack_app
        
        configured_app_id = "A123456"
        different_app_id = "A999999"
        bot_id = "B789012"
        
        with patch('api.webhooks.slack.utils.settings.slack_app_id', configured_app_id):
            result = await is_agent_own_slack_app(different_app_id, bot_id)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_slack_match_command_skips_tracked_message(self):
        """
        Business Rule: match_slack_command() must skip messages posted by agent.
        Behavior: Returns None when message_ts is tracked in Redis.
        """
        from api.webhooks.slack.utils import match_slack_command
        
        payload = {
            "event": {
                "type": "message",
                "text": "@agent help",
                "ts": "1234567890.123456",
                "bot_id": None
            }
        }
        
        with patch('api.webhooks.slack.utils.is_agent_posted_slack_message', new_callable=AsyncMock) as mock_check, \
             patch('api.webhooks.slack.utils.is_agent_own_slack_app', new_callable=AsyncMock, return_value=False):
            mock_check.return_value = True
            
            result = await match_slack_command(payload, "message")
            
            assert result is None
            mock_check.assert_called_once_with("1234567890.123456")
    
    @pytest.mark.asyncio
    async def test_slack_match_command_skips_own_app(self):
        """
        Business Rule: match_slack_command() must skip messages from agent's own app.
        Behavior: Returns None when app_id matches configured Slack app ID.
        """
        from api.webhooks.slack.utils import match_slack_command
        
        payload = {
            "event": {
                "type": "message",
                "text": "@agent help",
                "app_id": "A123456",
                "bot_id": None
            }
        }
        
        with patch('api.webhooks.slack.utils.is_agent_posted_slack_message', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.slack.utils.is_agent_own_slack_app', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            result = await match_slack_command(payload, "message")
            
            assert result is None
            mock_check.assert_called_once_with("A123456", None)
    
    @pytest.mark.asyncio
    async def test_slack_interactive_button_prevents_loop(self):
        """
        Business Rule: Interactive button actions must not create webhook loops.
        Behavior: Button actions mark messages as processed and don't trigger new webhook events.
        """
        from api.webhooks.slack.routes import slack_interactivity
        
        # This test will be implemented when we add button handlers
        # For now, we verify the structure exists
        assert callable(slack_interactivity)
