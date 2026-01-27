"""
Webhook payload models - strongly-typed Pydantic models for webhook payloads.

These models provide:
- Type safety and validation at API boundaries
- Helper methods for extracting commonly-needed data
- Extra field support for forward compatibility
"""

from enum import StrEnum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class WebhookSource(StrEnum):
    """Webhook source platforms."""
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"


class GitHubWebhookPayload(BaseModel):
    """
    Strongly-typed GitHub webhook payload.

    Handles issue_comment, pull_request, and issues events.
    Allows extra fields for forward compatibility.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    repository: Dict[str, Any] = Field(..., description="Repository object")
    comment: Optional[Dict[str, Any]] = Field(None, description="Comment object (for issue_comment events)")
    issue: Optional[Dict[str, Any]] = Field(None, description="Issue object")
    pull_request: Optional[Dict[str, Any]] = Field(None, description="Pull request object")
    sender: Optional[Dict[str, Any]] = Field(None, description="User who triggered the event")
    action: Optional[str] = Field(None, description="Event action (created, edited, etc)")
    routing: Optional[Dict[str, Any]] = Field(None, description="Routing metadata")
    classification: str = Field(default="SIMPLE", description="Task classification")
    user_content: Optional[str] = Field(None, alias="_user_content", description="Extracted user content")
    provider: str = Field(default="github", description="Provider name")

    def get_owner(self) -> str:
        """Extract repository owner login."""
        return self.repository.get("owner", {}).get("login", "")

    def get_repo_name(self) -> str:
        """Extract repository name."""
        return self.repository.get("name", "")

    def get_full_repo_name(self) -> str:
        """Get full repository name (owner/repo)."""
        owner = self.get_owner()
        repo = self.get_repo_name()
        return f"{owner}/{repo}" if owner and repo else ""

    def get_comment_id(self) -> Optional[int]:
        """Extract comment ID if present."""
        if self.comment:
            return self.comment.get("id")
        return None

    def get_comment_body(self) -> str:
        """Extract comment body if present."""
        if self.comment:
            return self.comment.get("body", "")
        return ""

    def get_issue_or_pr_number(self) -> Optional[int]:
        """Extract issue or PR number."""
        if self.issue:
            return self.issue.get("number")
        if self.pull_request:
            return self.pull_request.get("number")
        return None

    def get_sender_login(self) -> str:
        """Extract sender login."""
        if self.sender:
            return self.sender.get("login", "")
        return ""

    def get_sender_type(self) -> str:
        """Extract sender type (User, Bot, etc)."""
        if self.sender:
            return self.sender.get("type", "")
        return ""

    def is_pr_context(self) -> bool:
        """Check if this is a PR context (either PR event or issue with PR)."""
        if self.pull_request:
            return True
        if self.issue:
            return self.issue.get("pull_request") is not None
        return False


class JiraWebhookPayload(BaseModel):
    """
    Strongly-typed Jira webhook payload.

    Handles issue_created, issue_updated, and comment_created events.
    Allows extra fields for forward compatibility.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    issue: Dict[str, Any] = Field(..., description="Jira issue object")
    comment: Optional[Dict[str, Any]] = Field(None, description="Comment object")
    changelog: Optional[Dict[str, Any]] = Field(None, description="Changelog object")
    user: Optional[Dict[str, Any]] = Field(None, description="User who triggered the event")
    webhookEvent: Optional[str] = Field(None, description="Webhook event type")
    routing: Optional[Dict[str, Any]] = Field(None, description="Routing metadata")
    source_metadata: Optional[Dict[str, Any]] = Field(None, description="Source metadata")
    user_content: Optional[str] = Field(None, alias="_user_content", description="Extracted user content")
    provider: str = Field(default="jira", description="Provider name")

    def get_ticket_key(self) -> str:
        """Extract Jira ticket key."""
        return self.issue.get("key", "unknown")

    def get_issue_id(self) -> Optional[str]:
        """Extract Jira issue ID."""
        return self.issue.get("id")

    def get_summary(self) -> str:
        """Extract issue summary."""
        fields = self.issue.get("fields", {})
        return fields.get("summary", "")

    def get_description(self) -> str:
        """Extract issue description."""
        fields = self.issue.get("fields", {})
        description = fields.get("description", "")
        return self._safe_string(description)

    def get_comment_body(self) -> str:
        """Extract comment body if present."""
        if self.comment:
            body = self.comment.get("body", "")
            return self._safe_string(body)
        return ""

    def get_user_request(self) -> str:
        """
        Extract user request from various sources.

        Priority:
        1. user_content field (explicitly extracted)
        2. Comment body (for comment events)
        3. Issue description/summary (for issue events)
        """
        if self.user_content:
            return self.user_content

        if self.comment and self.comment.get("body"):
            return self.get_comment_body()

        description = self.get_description()
        if description:
            return description
        return self.get_summary()

    @staticmethod
    def _safe_string(value: Any) -> str:
        """
        Safely convert value to string.

        Handles Jira ADF (Atlassian Document Format) content.
        """
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # Handle ADF format
            if "content" in value:
                content = value.get("content", [])
                return JiraWebhookPayload._extract_adf_text(content)
            if "text" in value:
                return value.get("text", "")
        return str(value)

    @staticmethod
    def _extract_adf_text(content: list) -> str:
        """Extract text from Jira ADF content."""
        texts = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    texts.append(item["text"])
                elif "content" in item:
                    texts.append(JiraWebhookPayload._extract_adf_text(item["content"]))
        return " ".join(texts)


class SlackWebhookPayload(BaseModel):
    """
    Strongly-typed Slack webhook payload.

    Handles message events and interactive components.
    Allows extra fields for forward compatibility.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event: Dict[str, Any] = Field(..., description="Slack event object")
    type: Optional[str] = Field(None, description="Payload type (event_callback, etc)")
    team_id: Optional[str] = Field(None, description="Team ID")
    routing: Optional[Dict[str, Any]] = Field(None, description="Routing metadata")
    classification: str = Field(default="SIMPLE", description="Task classification")
    user_content: Optional[str] = Field(None, alias="_user_content", description="Extracted user content")
    provider: str = Field(default="slack", description="Provider name")

    def get_channel(self) -> Optional[str]:
        """Extract channel ID."""
        return self.event.get("channel")

    def get_thread_ts(self) -> Optional[str]:
        """Extract thread timestamp."""
        return self.event.get("ts")

    def get_text(self) -> str:
        """Extract message text."""
        return self.event.get("text", "")

    def get_user(self) -> Optional[str]:
        """Extract user ID."""
        return self.event.get("user")

    def get_event_type(self) -> str:
        """Extract event type."""
        return self.event.get("type", "")

    def is_bot_message(self) -> bool:
        """Check if message is from a bot."""
        return self.event.get("bot_id") is not None or self.event.get("subtype") == "bot_message"
