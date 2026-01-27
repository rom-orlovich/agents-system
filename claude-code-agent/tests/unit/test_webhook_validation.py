"""Unit tests for webhook validation module."""

import pytest
from core.webhook_validation import WebhookValidationResult
from api.webhooks.github.validation import validate_github_webhook, GitHubWebhookPayload
from api.webhooks.jira.validation import validate_jira_webhook, JiraWebhookPayload
from api.webhooks.slack.validation import validate_slack_webhook, SlackWebhookPayload


class TestGitHubWebhookValidation:
    """Test GitHub webhook input validation."""
    
    def test_comment_with_agent_review_passes(self):
        """Comment with @agent review should pass validation."""
        payload = {
            "action": "created",
            "comment": {
                "body": "@agent review please check the scroll button",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
        }
        
        result = validate_github_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_comment_without_agent_rejected(self):
        """Comment without @agent should be rejected."""
        payload = {
            "action": "created",
            "comment": {
                "body": "This is a regular comment without @agent",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "Expected invalid"
        assert "@agent" in result.error_message.lower()
    
    def test_pr_opened_without_agent_rejected(self):
        """PR opened without @agent should be rejected."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 456,
                "title": "Fix bug",
                "body": "This PR fixes a bug",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "testuser", "type": "User"}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "Expected invalid"
    
    def test_pr_opened_with_agent_passes(self):
        """PR opened with @agent should pass validation."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 456,
                "title": "Fix bug",
                "body": "@agent review this PR",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "testuser", "type": "User"}
        }
        
        result = validate_github_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_pr_synchronize_without_agent_rejected(self):
        """PR synchronize without @agent should be rejected."""
        payload = {
            "action": "synchronize",
            "pull_request": {
                "number": 456,
                "title": "Fix bug",
                "body": "Updated PR",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "testuser", "type": "User"}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "Expected invalid"
    
    def test_comment_with_invalid_command_rejected(self):
        """Comment with @agent but invalid command should be rejected."""
        payload = {
            "action": "created",
            "comment": {
                "body": "@agent invalidcommand",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "Expected invalid"
        assert "invalid command" in result.error_message.lower()
    
    def test_comment_with_valid_commands_passes(self):
        """Comment with @agent and valid commands should pass."""
        valid_commands = ["analyze", "plan", "fix", "review", "approve", "reject", "improve", "help"]
        
        for command in valid_commands:
            payload = {
                "action": "created",
                "comment": {
                    "body": f"@agent {command}",
                    "user": {"login": "testuser", "type": "User"}
                },
                "repository": {"full_name": "owner/repo"},
                "issue": {"number": 123}
            }
            
            result = validate_github_webhook(payload)
            assert result.is_valid, f"Command '{command}' should pass but got error: {result.error_message}"
    
    def test_issue_with_agent_passes(self):
        """Issue with @agent in title or body should pass."""
        payload = {
            "action": "opened",
            "issue": {
                "number": 789,
                "title": "@agent fix this issue",
                "body": "Please help",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        result = validate_github_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_github_webhook_no_text_content_rejected(self):
        """GitHub webhook with no text content should be rejected."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 456,
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "Expected invalid"
        assert "no text content" in result.error_message.lower()
    
    def test_bot_comment_without_agent_passes_validation(self):
        """Bot comment without @agent should pass validation (skip validation for bots)."""
        payload = {
            "action": "created",
            "comment": {
                "body": "❌ ❌ Separator is not found, and chunk exceed the limit",
                "user": {"login": "github-actions[bot]", "type": "Bot"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
            "sender": {"login": "github-actions[bot]", "type": "Bot"}
        }
        
        result = validate_github_webhook(payload)
        assert result.is_valid, f"Bot comment should pass validation but got error: {result.error_message}"
    
    def test_bot_comment_with_agent_passes_validation(self):
        """Bot comment with @agent should also pass validation."""
        payload = {
            "action": "created",
            "comment": {
                "body": "@agent review this",
                "user": {"login": "claude-agent", "type": "Bot"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
            "sender": {"login": "claude-agent", "type": "Bot"}
        }
        
        result = validate_github_webhook(payload)
        assert result.is_valid, f"Bot comment with @agent should pass validation but got error: {result.error_message}"
    
    def test_user_comment_without_agent_still_rejected(self):
        """User comment without @agent should still be rejected (existing behavior)."""
        payload = {
            "action": "created",
            "comment": {
                "body": "This is a regular comment",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
            "sender": {"login": "testuser", "type": "User"}
        }
        
        result = validate_github_webhook(payload)
        assert not result.is_valid, "User comment without @agent should be rejected"
        assert "@agent" in result.error_message.lower()


class TestJiraWebhookValidation:
    """Test Jira webhook input validation."""
    
    def test_jira_assignee_change_to_ai_passes(self):
        """Jira assignee change to AI agent should pass validation."""
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "assignee": {
                        "displayName": "AI Agent",
                        "accountId": "ai-agent-id"
                    }
                }
            },
            "changelog": {
                "items": [{
                    "field": "assignee",
                    "toString": "AI Agent"
                }]
            }
        }
        
        result = validate_jira_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_jira_comment_without_agent_rejected(self):
        """Jira comment without @agent should be rejected."""
        payload = {
            "webhookEvent": "comment_created",
            "comment": {
                "body": "This is a regular comment",
                "author": {
                    "displayName": "testuser",
                    "accountType": "atlassian"
                }
            },
            "issue": {
                "key": "PROJ-123"
            }
        }
        
        result = validate_jira_webhook(payload)
        assert not result.is_valid, "Expected invalid"
    
    def test_jira_comment_with_agent_passes(self):
        """Jira comment with @agent should pass validation."""
        payload = {
            "webhookEvent": "comment_created",
            "comment": {
                "body": "@agent review this issue",
                "author": {
                    "displayName": "testuser",
                    "accountType": "atlassian"
                }
            },
            "issue": {
                "key": "PROJ-123"
            }
        }
        
        result = validate_jira_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_jira_claude_agent_assignee_passes(self):
        """Jira assignee change to Claude Agent should pass."""
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "assignee": {
                        "displayName": "Claude Agent",
                        "accountId": "claude-agent-id"
                    }
                }
            },
            "changelog": {
                "items": [{
                    "field": "assignee",
                    "toString": "Claude Agent"
                }]
            }
        }
        
        result = validate_jira_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"


class TestSlackWebhookValidation:
    """Test Slack webhook input validation."""
    
    def test_slack_message_with_agent_passes(self):
        """Slack message with @agent should pass validation."""
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> @agent analyze this issue",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }
        
        result = validate_slack_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"
    
    def test_slack_message_without_agent_rejected(self):
        """Slack message without @agent should be rejected."""
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Hello, how are you?",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }
        
        result = validate_slack_webhook(payload)
        assert not result.is_valid, "Expected invalid"
        assert "@agent" in result.error_message.lower()
    
    def test_slack_message_no_text_rejected(self):
        """Slack message with no text should be rejected."""
        payload = {
            "event": {
                "type": "app_mention",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }
        
        result = validate_slack_webhook(payload)
        assert not result.is_valid, "Expected invalid"
        assert "no text" in result.error_message.lower()
    
    def test_slack_text_field_alternative(self):
        """Slack webhook with text field (not event.text) should work."""
        payload = {
            "text": "@agent help me",
            "event": {
                "type": "app_mention"
            }
        }
        
        result = validate_slack_webhook(payload)
        assert result.is_valid, f"Expected valid, got error: {result.error_message}"


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_github_payload_model(self):
        """Test GitHubWebhookPayload model."""
        payload = GitHubWebhookPayload(
            action="created",
            comment={"body": "@agent review"},
            repository={"full_name": "owner/repo"}
        )
        assert payload.extract_text() == "@agent review"
        result = payload.validate()
        assert result.is_valid
    
    def test_jira_payload_model(self):
        """Test JiraWebhookPayload model."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={"fields": {"assignee": {"displayName": "AI Agent"}}},
            changelog={"items": [{"field": "assignee", "toString": "AI Agent"}]}
        )
        result = payload.validate()
        assert result.is_valid
    
    def test_slack_payload_model(self):
        """Test SlackWebhookPayload model."""
        payload = SlackWebhookPayload(
            event={"text": "@agent analyze"},
            text=None
        )
        assert payload.extract_text() == "@agent analyze"
        result = payload.validate()
        assert result.is_valid
