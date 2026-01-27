"""
Jira webhook validation.
Pydantic models and validation logic for Jira webhooks.
"""

import re
from typing import Any, Dict, Optional
from pydantic import BaseModel
from core.webhook_validation import (
    WebhookValidationResult,
    extract_command,
    validate_command,
)
from core.config import settings


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload model."""
    webhookEvent: Optional[str] = None
    issue: Optional[Dict[str, Any]] = None
    changelog: Optional[Dict[str, Any]] = None
    comment: Optional[Dict[str, Any]] = None

    def validate(self) -> WebhookValidationResult:
        """Validate Jira webhook payload."""
        webhook_event = self.webhookEvent or ""
        
        if "issue_updated" in webhook_event.lower():
            changelog_items = self.changelog.get("items", []) if self.changelog else []
            assignee_changes = [
                item.get("toString", "")
                for item in changelog_items
                if item.get("field") == "assignee"
            ]
            assignee_name = ""
            if self.issue and self.issue.get("fields"):
                assignee_name = self.issue["fields"].get("assignee", {}).get("displayName", "")
            
            combined_text = " ".join(assignee_changes) + " " + assignee_name
            combined_lower = combined_text.lower().strip()
            if not combined_lower:
                return WebhookValidationResult.failure("Jira webhook does not meet activation rules")
            
            ai_agent_name = settings.jira_ai_agent_name or "AI Agent"
            if ai_agent_name.lower() in combined_lower:
                return WebhookValidationResult.success()
            if "claude agent" in combined_lower or "claude-agent" in combined_lower:
                return WebhookValidationResult.success()
            if "ai agent" in combined_lower or "ai-agent" in combined_lower:
                return WebhookValidationResult.success()
        
        if self.comment:
            from api.webhooks.jira.utils import extract_jira_comment_text
            comment_body = extract_jira_comment_text(self.comment.get("body", ""))
            if comment_body:
                command = extract_command(comment_body)
                is_valid, error_msg = validate_command(command)
                if is_valid:
                    return WebhookValidationResult.success()
        
        return WebhookValidationResult.failure("Jira webhook does not meet activation rules")


def validate_jira_webhook(payload: Dict[str, Any]) -> WebhookValidationResult:
    """Validate Jira webhook payload."""
    try:
        jira_payload = JiraWebhookPayload(**payload)
        return jira_payload.validate()
    except Exception as e:
        return WebhookValidationResult.failure(f"Invalid Jira webhook payload: {e}")
