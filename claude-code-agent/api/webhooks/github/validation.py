"""
GitHub webhook validation.
Pydantic models and validation logic for GitHub webhooks.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from core.webhook_validation import (
    WebhookValidationResult,
    extract_command,
    validate_command,
)
from api.webhooks.github.utils import extract_github_text


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload model."""
    action: Optional[str] = None
    comment: Optional[Dict[str, Any]] = None
    pull_request: Optional[Dict[str, Any]] = None
    issue: Optional[Dict[str, Any]] = None
    repository: Optional[Dict[str, Any]] = None

    def extract_text(self) -> str:
        """Extract text content from GitHub webhook."""
        comment_body_raw = self.comment.get("body", "") if self.comment else ""
        pr_title_raw = self.pull_request.get("title", "") if self.pull_request else ""
        pr_body_raw = self.pull_request.get("body", "") if self.pull_request else ""
        issue_title_raw = self.issue.get("title", "") if self.issue else ""
        issue_body_raw = self.issue.get("body", "") if self.issue else ""
        
        comment_body = extract_github_text(comment_body_raw)
        pr_title = extract_github_text(pr_title_raw)
        pr_body = extract_github_text(pr_body_raw)
        issue_title = extract_github_text(issue_title_raw)
        issue_body = extract_github_text(issue_body_raw)
        
        if comment_body:
            return comment_body
        elif pr_body:
            return f"{pr_title}{pr_body}"
        elif pr_title:
            return pr_title
        elif issue_body:
            return f"{issue_title}{issue_body}"
        elif issue_title:
            return issue_title
        return ""

    def validate(self) -> WebhookValidationResult:
        """Validate GitHub webhook payload."""
        text = self.extract_text()
        
        if not text:
            return WebhookValidationResult.failure("No text content found in GitHub webhook")
        
        command = extract_command(text)
        is_valid, error_msg = validate_command(command)
        
        if not is_valid:
            return WebhookValidationResult.failure(f"{error_msg} in GitHub webhook")
        
        return WebhookValidationResult.success()


def validate_github_webhook(payload: Dict[str, Any]) -> WebhookValidationResult:
    """Validate GitHub webhook payload."""
    try:
        # Check if sender is a bot - skip validation for bot comments
        sender = payload.get("sender", {})
        sender_login = sender.get("login", "")
        sender_type = sender.get("type", "")
        
        from core.command_matcher import is_bot_comment
        if is_bot_comment(sender_login, sender_type):
            return WebhookValidationResult.success()
        
        github_payload = GitHubWebhookPayload(**payload)
        return github_payload.validate()
    except Exception as e:
        return WebhookValidationResult.failure(f"Invalid GitHub webhook payload: {e}")
