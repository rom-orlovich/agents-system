"""Unit tests for CLI runner sensitive data sanitization."""

import pytest
from core.cli.claude import sanitize_sensitive_content


class TestSanitizeSensitiveContent:
    """Test sensitive content sanitization."""
    
    def test_sanitizes_jira_credentials(self):
        """Sanitize JIRA credentials from content."""
        content = "JIRA_EMAIL=test@example.com\nJIRA_API_TOKEN=secret-token-123"
        result = sanitize_sensitive_content(content)
        assert "JIRA_EMAIL=***REDACTED***" in result
        assert "JIRA_API_TOKEN=***REDACTED***" in result
        assert "test@example.com" not in result
        assert "secret-token-123" not in result
    
    def test_sanitizes_github_token(self):
        """Sanitize GitHub token from content."""
        content = "GITHUB_TOKEN=ghp_abcdef123456"
        result = sanitize_sensitive_content(content)
        assert "GITHUB_TOKEN=***REDACTED***" in result
        assert "ghp_abcdef123456" not in result
    
    def test_sanitizes_slack_tokens(self):
        """Sanitize Slack tokens from content."""
        content = "SLACK_BOT_TOKEN=xoxb-123\nSLACK_WEBHOOK_SECRET=secret456"
        result = sanitize_sensitive_content(content)
        assert "SLACK_BOT_TOKEN=***REDACTED***" in result
        assert "SLACK_WEBHOOK_SECRET=***REDACTED***" in result
        assert "xoxb-123" not in result
        assert "secret456" not in result
    
    def test_sanitizes_generic_passwords(self):
        """Sanitize generic password patterns."""
        content = "password=secret123\nPASSWORD=SECRET456\ntoken=abc123"
        result = sanitize_sensitive_content(content)
        assert "password=***REDACTED***" in result
        assert "PASSWORD=***REDACTED***" in result
        assert "token=***REDACTED***" in result
        assert "secret123" not in result
        assert "SECRET456" not in result
        assert "abc123" not in result
    
    def test_sanitizes_authorization_headers(self):
        """Sanitize Authorization headers."""
        content = "Authorization: Bearer token123\nAuthorization: Basic base64string"
        result = sanitize_sensitive_content(content)
        assert "Authorization: Bearer ***REDACTED***" in result
        assert "Authorization: Basic ***REDACTED***" in result
        assert "token123" not in result
        assert "base64string" not in result
    
    def test_preserves_non_sensitive_content(self):
        """Preserve non-sensitive content."""
        content = "This is a normal message with no secrets.\nIt contains regular text."
        result = sanitize_sensitive_content(content)
        assert result == content
    
    def test_handles_empty_content(self):
        """Handle empty content gracefully."""
        assert sanitize_sensitive_content("") == ""
        assert sanitize_sensitive_content(None) is None
    
    def test_sanitizes_mixed_content(self):
        """Sanitize sensitive data in mixed content."""
        content = """Task completed successfully.
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=token-123
Some other output here.
password=secret456"""
        result = sanitize_sensitive_content(content)
        assert "Task completed successfully" in result
        assert "Some other output here" in result
        assert "JIRA_EMAIL=***REDACTED***" in result
        assert "JIRA_API_TOKEN=***REDACTED***" in result
        assert "password=***REDACTED***" in result
        assert "user@example.com" not in result
        assert "token-123" not in result
        assert "secret456" not in result
