"""
Jira webhook validation.
Pydantic models and validation logic for Jira webhooks.
"""

import json
from typing import Any, Dict, Optional
from pydantic import BaseModel
from core.webhook_validation import (
    WebhookValidationResult,
    extract_command,
    validate_command,
)
from core.config import settings


def validate_response_format(result: str, format_type: str) -> tuple[bool, str]:
    # Defensive type conversion to prevent TypeError
    if result is None:
        result = ""
    elif isinstance(result, list):
        result = "\n".join(str(item) for item in result if item)
    elif not isinstance(result, str):
        result = str(result) if result else ""

    if format_type == "jira":
        try:
            adf_data = json.loads(result)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"

        if not isinstance(adf_data, dict):
            return False, "Invalid JSON format: expected object"

        if adf_data.get("type") != "doc":
            return False, "Missing ADF doc type (expected type='doc')"

        if "content" not in adf_data:
            return False, "Missing content array"

        return True, ""

    else:
        return False, f"Unknown format type: {format_type}"


def _safe_string(value: Any, default: str = "") -> str:
    """
    Safely convert a value to a string.
    
    Handles cases where Jira webhook fields might be lists or other non-string types.
    
    Args:
        value: Value to convert (can be str, list, dict, None, etc.)
        default: Default value to return if value is None or empty
        
    Returns:
        String representation of the value
    """
    if value is None:
        return default
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, list):
        if not value:
            return default
        return " ".join(str(item) for item in value if item)
    
    return str(value) if value else default


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload model."""
    webhookEvent: Optional[str] = None
    issue: Optional[Dict[str, Any]] = None
    changelog: Optional[Dict[str, Any]] = None
    comment: Optional[Dict[str, Any]] = None

    def validate(self) -> WebhookValidationResult:
        webhook_event_raw = self.webhookEvent or ""
        webhook_event = _safe_string(webhook_event_raw)
        
        if "issue_updated" in webhook_event.lower():
            changelog_items = self.changelog.get("items", []) if self.changelog else []
            assignee_changes = [
                _safe_string(item.get("toString", ""))
                for item in changelog_items
                if item.get("field") == "assignee"
            ]
            assignee_name = ""
            if self.issue and self.issue.get("fields"):
                assignee = self.issue["fields"].get("assignee")
                if assignee:
                    if isinstance(assignee, dict):
                        assignee_name = _safe_string(assignee.get("displayName", ""))
                    else:
                        assignee_name = _safe_string(assignee)
            
            combined_text = " ".join(assignee_changes) + " " + assignee_name
            combined_lower = combined_text.lower().strip()
            if not combined_lower:
                return WebhookValidationResult.failure("Jira webhook does not meet activation rules")
            
            ai_agent_name = _safe_string(settings.jira_ai_agent_name or "AI Agent")
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
