"""
Slack Bot Service
=================
Slack integration using the official Slack SDK (no MCP server for Slack).
"""

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from shared.config import get_settings

logger = structlog.get_logger(__name__)


class SlackBot:
    """Slack bot for notifications and interactions."""

    def __init__(self):
        settings = get_settings()
        self.client = WebClient(token=settings.slack.bot_token)
        self.channel_agents = settings.slack.channel_agents
        self.channel_errors = settings.slack.channel_errors

    def send_message(self, text: str, channel: str | None = None) -> bool:
        """Send a simple text message."""
        try:
            self.client.chat_postMessage(
                channel=channel or self.channel_agents,
                text=text,
            )
            return True
        except SlackApiError as e:
            logger.error("Failed to send Slack message", error=str(e))
            return False

    def send_planning_notification(
        self,
        ticket_id: str,
        summary: str,
        pr_url: str,
        branch: str,
    ):
        """Send notification that planning is complete."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 Plan Ready for Review: {ticket_id}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:* {summary}\n*Branch:* `{branch}`",
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 View PR"},
                        "url": pr_url,
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve"},
                        "value": f"approve:{ticket_id}",
                        "action_id": "approve_plan",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject"},
                        "value": f"reject:{ticket_id}",
                        "action_id": "reject_plan",
                        "style": "danger",
                    },
                ],
            },
        ]

        try:
            self.client.chat_postMessage(
                channel=self.channel_agents,
                text=f"Plan ready for {ticket_id}",
                blocks=blocks,
            )
            logger.info("Sent planning notification", ticket_id=ticket_id)
            return True
        except SlackApiError as e:
            logger.error("Failed to send planning notification", error=str(e))
            return False

    def send_execution_complete(
        self,
        ticket_id: str,
        pr_url: str,
        tests_passed: int,
        tests_failed: int,
    ):
        """Send notification that execution is complete."""
        status_emoji = "✅" if tests_failed == 0 else "⚠️"
        text = (
            f"{status_emoji} *Execution Complete:* {ticket_id}\n"
            f"Tests: {tests_passed} passed, {tests_failed} failed\n"
            f"<{pr_url}|View PR>"
        )

        self.send_message(text)

    def send_error_alert(
        self,
        title: str,
        error_message: str,
        sentry_link: str | None = None,
        jira_ticket: str | None = None,
    ):
        """Send error alert to errors channel."""
        text = f"🚨 *Error Alert:* {title}\n```{error_message[:500]}```"

        if sentry_link:
            text += f"\n<{sentry_link}|View in Sentry>"
        if jira_ticket:
            text += f"\nJira: {jira_ticket}"

        self.send_message(text, channel=self.channel_errors)

    def send_agent_status(
        self,
        ticket_id: str,
        agent: str,
        status: str,
        message: str,
    ):
        """Send agent status update."""
        emoji_map = {
            "discovery": "🔍",
            "planning": "📋",
            "execution": "⚙️",
            "cicd": "🔄",
        }
        emoji = emoji_map.get(agent.lower(), "🤖")

        text = f"{emoji} *{agent}* | {ticket_id}\nStatus: {status}\n{message}"
        self.send_message(text)


# Singleton instance
_bot: SlackBot | None = None


def get_slack_bot() -> SlackBot:
    """Get singleton SlackBot instance."""
    global _bot
    if _bot is None:
        _bot = SlackBot()
    return _bot
