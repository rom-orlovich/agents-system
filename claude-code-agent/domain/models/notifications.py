"""
Notification models - standardized models for task notifications.

These models define the structure of notifications sent to Slack
after task completion.
"""

import os
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from domain.models.webhook_payload import WebhookSource


class TaskSummary(BaseModel):
    """
    Task summary extracted from task result.

    Contains structured information about what the task accomplished.
    """
    summary: str = Field(..., description="Brief summary of task result")
    classification: str = Field(default="SIMPLE", description="Task classification")
    what_was_done: Optional[str] = Field(None, description="Description of what was done")
    key_insights: Optional[str] = Field(None, description="Key insights from the task")

    def to_slack_text(self) -> str:
        """Format summary for Slack display."""
        lines = [f"*Summary:* {self.summary}"]
        if self.what_was_done:
            lines.append(f"*What was done:* {self.what_was_done}")
        if self.key_insights:
            lines.append(f"*Key insights:* {self.key_insights}")
        return "\n".join(lines)


class TaskNotification(BaseModel):
    """
    Task notification for Slack.

    Contains all information needed to send a notification to Slack
    about a completed task.
    """
    # Required fields
    task_id: str = Field(..., description="Task identifier")
    source: WebhookSource = Field(..., description="Source platform")
    command: str = Field(..., description="Command that was executed")
    success: bool = Field(..., description="Whether task succeeded")

    # Optional fields
    result: Optional[str] = Field(None, description="Task result preview")
    error: Optional[str] = Field(None, description="Error message")
    pr_url: Optional[str] = Field(None, description="PR URL if applicable")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Task cost")
    user_request: Optional[str] = Field(None, description="Original user request")
    ticket_key: Optional[str] = Field(None, description="Jira ticket key")
    routing: Optional[Dict[str, Any]] = Field(None, description="Routing metadata")

    def get_default_channel(self) -> str:
        """Get the default Slack channel for this notification."""
        if self.success:
            return os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")
        return os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors")

    def get_status_emoji(self) -> str:
        """Get status emoji for notification."""
        return "✅" if self.success else "❌"

    def get_status_text(self) -> str:
        """Get status text for notification."""
        return "Completed" if self.success else "Failed"

    def get_summary_text(self) -> str:
        """Get summary text for notification."""
        emoji = self.get_status_emoji()
        status = self.get_status_text()
        return f"{emoji} Task {status} - {self.source.value.title()} - {self.command}"

    def build_slack_blocks(self) -> list:
        """
        Build Slack Block Kit blocks for the notification.

        Returns a list of block dictionaries for the Slack API.
        """
        blocks = []

        # Header section
        status_emoji = self.get_status_emoji()
        status_text = self.get_status_text()
        header_text = (
            f"{status_emoji} *Task {status_text}*\n"
            f"*Source:* {self.source.value.title()}\n"
            f"*Command:* {self.command}\n"
            f"*Task ID:* `{self.task_id}`"
        )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text,
            }
        })

        # Result section (for success)
        if self.success and self.result:
            result_preview = self.result[:500] + "..." if len(self.result) > 500 else self.result
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Result:*\n```{result_preview}```",
                }
            })

        # Error section (for failure)
        if self.error:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```{self.error}```",
                }
            })

        # Cost section
        if self.cost_usd > 0:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"💰 Cost: ${self.cost_usd:.4f}",
                }]
            })

        # PR/Ticket links
        if self.pr_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔗 <{self.pr_url}|View Pull Request>",
                }
            })

        if self.ticket_key:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"🎫 Jira: `{self.ticket_key}`",
                }]
            })

        return blocks
