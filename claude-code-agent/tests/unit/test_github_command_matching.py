"""Unit tests for GitHub command matching logic.

Tests ensure only valid @agent commands from users (not the agent itself) trigger processing.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from api.webhooks.github.utils import match_github_command
from core.webhook_configs import GITHUB_WEBHOOK


class TestGitHubCommandMatching:
    """Test GitHub command matching and infinite loop prevention."""
    
    @pytest.mark.asyncio
    async def test_agent_own_comment_with_valid_command_does_not_trigger(self):
        """Agent's own comment with valid @agent review should NOT trigger."""
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": "@agent review this PR",
                "user": {"login": "agent-user", "type": "User"}
            },
            "sender": {"login": "agent-user", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is not None, "User comment should trigger processing"
    
    @pytest.mark.asyncio
    async def test_invalid_command_does_not_trigger(self):
        """Comment with @agent but invalid command should NOT trigger."""
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": "@agent invalidcommand",
                "user": {"login": "testuser", "type": "User"}
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is None, "Invalid command should not trigger processing"
    
    @pytest.mark.asyncio
    async def test_comment_without_agent_does_not_trigger(self):
        """Comment without @agent should NOT trigger."""
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": "This is a regular comment",
                "user": {"login": "testuser", "type": "User"}
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is None, "Comment without @agent should not trigger"
    
    @pytest.mark.asyncio
    async def test_valid_command_from_user_triggers(self):
        """Valid @agent review from user SHOULD trigger."""
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": "@agent review this PR",
                "user": {"login": "real-user", "type": "User"}
            },
            "sender": {"login": "real-user", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is not None, "Valid command from user should trigger"
            assert result.name == "review", f"Expected 'review' command, got {result.name}"
    
    @pytest.mark.asyncio
    async def test_posted_comment_id_does_not_trigger(self):
        """Comment ID that was posted by agent should NOT trigger."""
        payload = {
            "action": "created",
            "comment": {
                "id": 999,
                "body": "@agent review this PR",
                "user": {"login": "real-user", "type": "User"}
            },
            "sender": {"login": "real-user", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=True):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is None, "Posted comment ID should not trigger"
    
    @pytest.mark.asyncio
    async def test_bot_comment_does_not_trigger(self):
        """Bot comments should NOT trigger even with valid @agent command."""
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": "@agent review this PR",
                "user": {"login": "github-actions[bot]", "type": "Bot"}
            },
            "sender": {"login": "github-actions[bot]", "type": "Bot"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        result = await match_github_command(payload, "issue_comment.created")
        assert result is None, "Bot comments should not trigger"
