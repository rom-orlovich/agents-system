import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from domain.models.webhook_payload import WebhookSource


class TaskSummary(BaseModel):
    summary: str
    classification: str = "SIMPLE"
    what_was_done: Optional[str] = None
    key_insights: Optional[str] = None

    def to_slack_text(self) -> str:
        lines = [f"*Summary:* {self.summary}"]
        if self.what_was_done:
            lines.append(f"*What was done:* {self.what_was_done}")
        if self.key_insights:
            lines.append(f"*Key insights:* {self.key_insights}")
        return "\n".join(lines)


class TaskNotification(BaseModel):
    task_id: str
    source: WebhookSource
    command: str
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    pr_url: Optional[str] = None
    cost_usd: float = 0.0
    user_request: Optional[str] = None
    ticket_key: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None

    def get_default_channel(self) -> str:
        if self.success:
            return os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")
        return os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors")

    def get_status_emoji(self) -> str:
        return "✅" if self.success else "❌"

    def get_status_text(self) -> str:
        return "Completed" if self.success else "Failed"

    def get_summary_text(self) -> str:
        emoji = self.get_status_emoji()
        status = self.get_status_text()
        return f"{emoji} Task {status} - {self.source.value.title()} - {self.command}"

    def build_slack_blocks(self) -> List[Dict[str, Any]]:
        blocks = []

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
            "text": {"type": "mrkdwn", "text": header_text}
        })

        if self.success and self.result:
            result_preview = self.result[:500] + "..." if len(self.result) > 500 else self.result
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Result:*\n```{result_preview}```"}
            })

        if self.error:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Error:*\n```{self.error}```"}
            })

        if self.cost_usd > 0:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"💰 Cost: ${self.cost_usd:.4f}"}]
            })

        if self.pr_url:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🔗 <{self.pr_url}|View Pull Request>"}
            })

        if self.ticket_key:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🎫 Jira: `{self.ticket_key}`"}]
            })

        return blocks
