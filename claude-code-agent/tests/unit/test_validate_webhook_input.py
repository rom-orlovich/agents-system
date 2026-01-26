"""Unit tests for webhook input validation script."""

import json
import subprocess
import pytest
from pathlib import Path


def run_validation_script(payload: dict) -> tuple[int, str, str]:
    """
    Run the validate-webhook-input.sh script with given payload.
    
    Returns:
        (exit_code, stdout, stderr)
    """
    script_path = Path(__file__).parent.parent.parent / "scripts" / "validate-webhook-input.sh"
    
    if not script_path.exists():
        pytest.skip(f"Validation script not found at {script_path}")
    
    result = subprocess.run(
        [str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=5
    )
    
    return result.returncode, result.stdout, result.stderr


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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"


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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"


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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
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
        
        exit_code, stdout, stderr = run_validation_script(payload)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
