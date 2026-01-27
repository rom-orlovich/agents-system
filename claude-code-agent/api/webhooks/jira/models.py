"""
Pydantic models for Jira webhook operations.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class JiraTaskCompletionPayload(BaseModel):
    """Pydantic model for Jira task completion payload."""
    
    issue: Dict[str, Any] = Field(..., description="Jira issue object")
    comment: Optional[Dict[str, Any]] = Field(None, description="Jira comment object")
    changelog: Optional[Dict[str, Any]] = Field(None, description="Jira changelog object")
    user_content: Optional[str] = Field(None, alias="_user_content", description="User content from webhook")
    routing: Optional[Dict[str, Any]] = Field(None, description="Routing metadata")
    source_metadata: Optional[Dict[str, Any]] = Field(None, description="Source metadata")
    
    model_config = {"populate_by_name": True}
    
    def get_ticket_key(self) -> str:
        """Extract ticket key from issue."""
        return self.issue.get("key", "unknown")
    
    def get_user_request(self) -> str:
        """Extract user request from various sources."""
        if self.user_content:
            return self.user_content
        
        if self.comment and self.comment.get("body"):
            from api.webhooks.jira.utils import extract_jira_comment_text
            comment_body = extract_jira_comment_text(self.comment.get("body", ""))
            if "@agent" in comment_body.lower():
                from core.command_matcher import extract_command
                result_cmd = extract_command(comment_body)
                if result_cmd:
                    _, user_content = result_cmd
                    return user_content.strip()
            return comment_body.strip()
        
        if self.issue and self.issue.get("fields"):
            fields = self.issue.get("fields", {})
            description = fields.get("description", "")
            summary = fields.get("summary", "")
            return description or summary
        
        return ""


class SlackNotificationRequest(BaseModel):
    """Pydantic model for Slack notification request."""
    
    task_id: str = Field(..., description="Task identifier")
    webhook_source: str = Field(..., description="Webhook source (e.g., 'jira')")
    command: str = Field(..., description="Command that was executed")
    success: bool = Field(..., description="Whether task succeeded")
    result: Optional[str] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Task error")
    pr_url: Optional[str] = Field(None, description="Pull request URL")
    payload: Optional[Dict[str, Any]] = Field(None, description="Original payload")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Task cost in USD")
    user_request: Optional[str] = Field(None, description="User's original request")
    ticket_key: Optional[str] = Field(None, description="Jira ticket key")


class JiraTaskCommentRequest(BaseModel):
    """Pydantic model for Jira task comment request."""
    
    issue: Dict[str, Any] = Field(..., description="Jira issue object")
    message: str = Field(..., description="Comment message")
    success: bool = Field(..., description="Whether task succeeded")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Task cost in USD")
    pr_url: Optional[str] = Field(None, description="Pull request URL")
    
    def get_issue_key(self) -> Optional[str]:
        """Extract issue key from issue object."""
        return self.issue.get("key")


class TaskSummary(BaseModel):
    """Pydantic model for task summary."""
    
    summary: str = Field(..., description="Task summary")
    classification: str = Field(default="SIMPLE", description="Task classification")
    what_was_done: Optional[str] = Field(None, description="What was done")
    key_insights: Optional[str] = Field(None, description="Key insights")


class RoutingMetadata(BaseModel):
    """Pydantic model for routing metadata."""
    
    repo: Optional[str] = Field(None, description="Repository (owner/repo)")
    pr_number: Optional[int] = Field(None, gt=0, description="Pull request number")
    
    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: Optional[int]) -> Optional[int]:
        """Validate PR number is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("PR number must be positive")
        return v


class PRRouting(BaseModel):
    """Pydantic model for PR routing information."""
    
    repo: str = Field(..., description="Repository (owner/repo)")
    pr_number: int = Field(..., gt=0, description="Pull request number")
    
    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        """Validate PR number is positive."""
        if v <= 0:
            raise ValueError("PR number must be positive")
        return v
