"""Slack API client wrapper."""

from typing import Optional, Dict, Any, List
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from shared.config import settings


class SlackClient:
    """Slack API client."""

    def __init__(self, token: Optional[str] = None):
        """Initialize Slack client.

        Args:
            token: Slack bot token (optional, uses settings if not provided)
        """
        self.token = token or settings.SLACK_BOT_TOKEN
        self.client = AsyncWebClient(token=self.token) if self.token else None

    async def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Send a message to a Slack channel.

        Args:
            channel: Channel ID or name
            text: Plain text message
            blocks: Block Kit blocks

        Returns:
            Message timestamp or None
        """
        if not self.client:
            print(f"Slack not configured, would send to {channel}: {text}")
            return None

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            return response["ts"]
        except SlackApiError as e:
            print(f"Error sending Slack message: {e.response['error']}")
            return None

    async def send_plan_approval_request(
        self,
        task_id: str,
        repository: str,
        risk_level: str,
        estimated_minutes: int,
        pr_url: str,
        cost_usd: Optional[float] = None,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """Send plan approval request.

        Args:
            task_id: Task identifier
            repository: Repository name
            risk_level: Risk level (low/medium/high)
            estimated_minutes: Estimated execution time
            pr_url: Pull request URL
            channel: Slack channel (optional, uses default)

        Returns:
            Message timestamp or None
        """
        channel = channel or settings.SLACK_CHANNEL_AGENTS

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤖 New AI Fix Plan Ready for Review"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Task ID:*\n`{task_id}`"},
                    {"type": "mrkdwn", "text": f"*Repository:*\n{repository}"},
                    {"type": "mrkdwn", "text": f"*Risk Level:*\n{risk_level.upper()}"},
                    {"type": "mrkdwn", "text": f"*Cost:*\n${cost_usd:.4f}" if cost_usd is not None else f"*Est. Time:*\n{estimated_minutes} min"}
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 View Plan"},
                        "url": pr_url,
                        "action_id": "view_plan"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve"},
                        "style": "primary",
                        "action_id": "approve_task",
                        "value": task_id
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject"},
                        "style": "danger",
                        "action_id": "reject_task",
                        "value": task_id
                    }
                ]
            }
        ]

        return await self.send_message(
            channel=channel,
            text=f"New plan ready for task {task_id}",
            blocks=blocks
        )

    async def send_execution_started(
        self,
        task_id: str,
        repository: str,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """Send execution started notification.

        Args:
            task_id: Task identifier
            repository: Repository name
            channel: Slack channel (optional)

        Returns:
            Message timestamp or None
        """
        channel = channel or settings.SLACK_CHANNEL_AGENTS

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚙️ *Execution Started*\n\nTask `{task_id}` is now being executed in `{repository}`"
                }
            }
        ]

        return await self.send_message(
            channel=channel,
            text=f"Execution started for {task_id}",
            blocks=blocks
        )

    async def send_task_completed(
        self,
        task_id: str,
        repository: str,
        pr_url: str,
        execution_time: str,
        cost_usd: Optional[float] = None,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """Send task completed notification.

        Args:
            task_id: Task identifier
            repository: Repository name
            pr_url: Pull request URL
            execution_time: Execution duration
            channel: Slack channel (optional)

        Returns:
            Message timestamp or None
        """
        channel = channel or settings.SLACK_CHANNEL_AGENTS

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Task Completed Successfully"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Task ID:*\n`{task_id}`"},
                    {"type": "mrkdwn", "text": f"*Repository:*\n{repository}"},
                    {"type": "mrkdwn", "text": f"*Execution Time:*\n{execution_time}"},
                    {"type": "mrkdwn", "text": f"*Cost:*\n${cost_usd:.4f}" if cost_usd is not None else f"*PR:*\n<{pr_url}|View PR>"}
                ]
            }
        ]
        
        # Add PR link as a second row if cost is present
        if cost_usd is not None:
             blocks[1]["fields"].append({"type": "mrkdwn", "text": f"*PR:*\n<{pr_url}|View PR>"})

        return await self.send_message(
            channel=channel,
            text=f"Task {task_id} completed",
            blocks=blocks
        )

    async def send_task_failed(
        self,
        task_id: str,
        error: str,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """Send task failed notification.

        Args:
            task_id: Task identifier
            error: Error message
            channel: Slack channel (optional)

        Returns:
            Message timestamp or None
        """
        channel = channel or settings.SLACK_CHANNEL_ERRORS

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "❌ Task Failed"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Task ID:*\n`{task_id}`"},
                    {"type": "mrkdwn", "text": f"*Error:*\n```{error}```"}
                ]
            }
        ]

        return await self.send_message(
            channel=channel,
            text=f"Task {task_id} failed",
            blocks=blocks
        )

    async def reply_in_thread(
        self,
        channel: str,
        thread_ts: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Reply in a thread.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp to reply to
            text: Message text
            blocks: Optional Block Kit blocks

        Returns:
            Message timestamp or None
        """
        if not self.client:
            print(f"Slack not configured, would reply in {channel}/{thread_ts}: {text}")
            return None

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=text,
                blocks=blocks
            )
            return response["ts"]
        except SlackApiError as e:
            print(f"Error replying in thread: {e.response['error']}")
            return None

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str
    ) -> bool:
        """Add a reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            reaction: Emoji name (without colons)

        Returns:
            True if successful
        """
        if not self.client:
            print(f"Slack not configured, would add :{reaction}: to message")
            return False

        try:
            await self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
            return True
        except SlackApiError as e:
            print(f"Error adding reaction: {e.response['error']}")
            return False
