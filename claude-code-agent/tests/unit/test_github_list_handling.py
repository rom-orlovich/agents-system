"""TDD tests for GitHub webhook list value handling."""

import pytest
from unittest.mock import AsyncMock, patch


class TestGitHubListHandling:
    """Test that GitHub webhook handlers correctly handle list values."""
    
    def test_extract_github_text_converts_list_to_string(self):
        """
        Business Rule: List values must be converted to strings safely.
        Behavior: extract_github_text() converts lists to space-separated strings.
        """
        from api.webhooks.github.utils import extract_github_text
        
        assert extract_github_text(["item1", "item2"]) == "item1 item2"
        assert extract_github_text(["single"]) == "single"
        assert extract_github_text([]) == ""
        assert extract_github_text(None) == ""
        assert extract_github_text("string") == "string"
        assert extract_github_text(123) == "123"
    
    def test_extract_github_text_handles_dict(self):
        """
        Business Rule: extract_github_text() must handle dict values.
        Behavior: Function extracts text from dict with 'text', 'body', or 'content' keys.
        """
        from api.webhooks.github.utils import extract_github_text
        
        assert extract_github_text({"text": "hello"}) == "hello"
        assert extract_github_text({"body": "world"}) == "world"
        assert extract_github_text({"content": "test"}) == "test"
        assert extract_github_text({"other": "key"}) == "{'other': 'key'}"
    
    @pytest.mark.asyncio
    async def test_match_github_command_handles_list_body(self):
        """
        Business Rule: match_github_command() must handle list values in comment body.
        Behavior: Function works correctly when body is a list instead of a string.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": ["@agent", "review", "this", "PR"],
                "user": {"login": "testuser", "type": "User"}
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is not None, "List body should be converted and command matched"
            assert result.name == "review"
    
    @pytest.mark.asyncio
    async def test_match_github_command_handles_dict_body(self):
        """
        Business Rule: match_github_command() must handle dict values in comment body.
        Behavior: Function works correctly when body is a dict instead of a string.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": {"text": "@agent review this PR"},
                "user": {"login": "testuser", "type": "User"}
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is not None, "Dict body should be converted and command matched"
            assert result.name == "review"
    
    @pytest.mark.asyncio
    async def test_match_github_command_handles_none_body(self):
        """
        Business Rule: match_github_command() must handle None values in comment body.
        Behavior: Function returns None gracefully when body is None.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "created",
            "comment": {
                "id": 123,
                "body": None,
                "user": {"login": "testuser", "type": "User"}
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }
        
        with patch("api.webhooks.github.utils.is_agent_posted_comment", new_callable=AsyncMock, return_value=False):
            result = await match_github_command(payload, "issue_comment.created")
            assert result is None, "None body should not match any command"
    
    @pytest.mark.asyncio
    async def test_match_github_command_handles_list_issue_body(self):
        """
        Business Rule: match_github_command() must handle list values in issue body.
        Behavior: Function works correctly when issue body is a list instead of a string.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "opened",
            "issue": {
                "number": 456,
                "body": ["@agent", "analyze", "this", "issue"],
                "title": "Test Issue"
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"}
        }
        
        result = await match_github_command(payload, "issues.opened")
        assert result is not None, "List issue body should be converted and command matched"
        assert result.name == "analyze"
    
    @pytest.mark.asyncio
    async def test_match_github_command_handles_list_pr_body(self):
        """
        Business Rule: match_github_command() must handle list values in PR body.
        Behavior: Function works correctly when PR body is a list instead of a string.
        """
        from api.webhooks.github.utils import match_github_command
        
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 789,
                "body": ["@agent", "review", "this", "PR"],
                "title": "Test PR"
            },
            "sender": {"login": "testuser", "type": "User"},
            "repository": {"full_name": "owner/repo"}
        }
        
        result = await match_github_command(payload, "pull_request.opened")
        assert result is not None, "List PR body should be converted and command matched"
        assert result.name == "review"
    
    def test_github_webhook_payload_extract_text_handles_list(self):
        """
        Business Rule: GitHubWebhookPayload.extract_text() must handle list values.
        Behavior: extract_text() works correctly when body fields are lists.
        """
        from api.webhooks.github.validation import GitHubWebhookPayload
        
        payload = GitHubWebhookPayload(
            comment={"body": ["@agent", "review", "test"]},
            issue=None,
            pull_request=None,
            repository=None
        )
        
        text = payload.extract_text()
        assert text == "@agent review test", "List comment body should be converted to string"
    
    def test_github_webhook_payload_extract_text_handles_dict(self):
        """
        Business Rule: GitHubWebhookPayload.extract_text() must handle dict values.
        Behavior: extract_text() works correctly when body fields are dicts.
        """
        from api.webhooks.github.validation import GitHubWebhookPayload
        
        payload = GitHubWebhookPayload(
            comment={"body": {"text": "@agent review test"}},
            issue=None,
            pull_request=None,
            repository=None
        )
        
        text = payload.extract_text()
        assert text == "@agent review test", "Dict comment body should extract text"
    
    def test_extract_command_handles_list_input(self):
        """
        Business Rule: extract_command() must handle list input as defensive check.
        Behavior: Function converts list to string before processing.
        """
        from core.command_matcher import extract_command
        
        result = extract_command(["@agent", "review", "test"])
        assert result is not None, "List input should be converted and command extracted"
        command_name, user_content = result
        assert command_name == "review"
        assert user_content == "test"
    
    def test_extract_command_handles_dict_input(self):
        """
        Business Rule: extract_command() must handle dict input as defensive check.
        Behavior: Function converts dict to string before processing.
        Note: If the string representation contains the pattern, it will match.
        """
        from core.command_matcher import extract_command
        
        result = extract_command({"text": "@agent review test"})
        assert result is not None, "Dict input converted to string should match if pattern exists"
        command_name, user_content = result
        assert command_name == "review", "Command should be extracted from dict string representation"
    
    def test_extract_command_handles_none_input(self):
        """
        Business Rule: extract_command() must handle None input gracefully.
        Behavior: Function returns None when input is None.
        """
        from core.command_matcher import extract_command
        
        result = extract_command(None)
        assert result is None, "None input should return None"
    
    def test_extract_command_handles_integer_input(self):
        """
        Business Rule: extract_command() must handle non-string input as defensive check.
        Behavior: Function converts integer to string before processing.
        """
        from core.command_matcher import extract_command
        
        result = extract_command(12345)
        assert result is None, "Integer input should be converted but won't match pattern"
