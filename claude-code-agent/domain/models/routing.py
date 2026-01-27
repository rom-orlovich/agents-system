"""
Routing models - metadata for routing tasks to their destinations.

These models define where task results should be sent:
- GitHub PRs/issues
- Jira tickets
- Slack channels/threads
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RoutingMetadata(BaseModel):
    """
    Routing metadata for task completion.

    Contains information about where to route task results.
    All fields are optional since different sources use different routing info.
    """
    # GitHub routing
    repo: Optional[str] = Field(None, description="Repository (owner/repo)")
    pr_number: Optional[int] = Field(None, description="Pull request number")

    # Jira routing
    ticket_key: Optional[str] = Field(None, description="Jira ticket key (e.g., PROJ-123)")

    # Slack routing
    slack_channel: Optional[str] = Field(None, description="Slack channel ID")
    slack_thread_ts: Optional[str] = Field(None, description="Slack thread timestamp")

    # Generic routing
    source: Optional[str] = Field(None, description="Source platform (github, jira, slack)")

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: Optional[int]) -> Optional[int]:
        """Validate PR number is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("PR number must be positive")
        return v

    def has_github_routing(self) -> bool:
        """Check if GitHub routing info is present."""
        return bool(self.repo and self.pr_number)

    def has_jira_routing(self) -> bool:
        """Check if Jira routing info is present."""
        return bool(self.ticket_key)

    def has_slack_routing(self) -> bool:
        """Check if Slack routing info is present."""
        return bool(self.slack_channel)

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class PRRouting(BaseModel):
    """
    Required PR routing information.

    Use this when GitHub PR routing is required (not optional).
    """
    repo: str = Field(..., description="Repository (owner/repo)")
    pr_number: int = Field(..., gt=0, description="Pull request number")

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        """Validate PR number is positive."""
        if v <= 0:
            raise ValueError("PR number must be positive")
        return v

    def get_owner(self) -> str:
        """Extract owner from repo string."""
        parts = self.repo.split("/")
        return parts[0] if len(parts) >= 2 else ""

    def get_repo_name(self) -> str:
        """Extract repo name from repo string."""
        parts = self.repo.split("/")
        return parts[1] if len(parts) >= 2 else self.repo

    def to_routing_metadata(self) -> RoutingMetadata:
        """Convert to RoutingMetadata."""
        return RoutingMetadata(
            repo=self.repo,
            pr_number=self.pr_number,
            source="github",
        )


class SourceMetadata(BaseModel):
    """
    Source metadata stored with tasks.

    Contains all information about where a task came from and how to complete it.
    """
    webhook_source: str = Field(..., description="Source platform (github, jira, slack)")
    webhook_name: str = Field(..., description="Name of the webhook configuration")
    command: str = Field(..., description="Command that was matched")
    original_target_agent: Optional[str] = Field(None, description="Originally targeted agent")
    routing: Optional[RoutingMetadata] = Field(None, description="Routing metadata")
    completion_handler: str = Field(..., description="Module path for completion handler")
    flow_id: Optional[str] = Field(None, description="Conversation flow ID")
    external_id: Optional[str] = Field(None, description="External unique ID")
    claude_task_id: Optional[str] = Field(None, description="Claude tasks sync ID")

    def to_json_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        data = self.model_dump()
        if self.routing:
            data["routing"] = self.routing.to_dict()
        return data
