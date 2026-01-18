"""
Slack Service
=============
Real integration with Slack API.
"""

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import List, Dict, Any, Optional

from config import settings

logger = structlog.get_logger(__name__)


class SlackService:
    """Service for interacting with Slack API."""
    
    def __init__(self):
        """Initialize Slack client."""
        self.client = WebClient(token=settings.slack.bot_token)
        self.default_channel = settings.slack.channel_agents
        logger.info("slack_service_initialized")
    
    def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send a message to a Slack channel.
        
        Args:
            text: Message text
            channel: Channel to send to (defaults to configured agents channel)
            blocks: Optional Block Kit blocks for rich formatting
            
        Returns:
            True if successful
        """
        target_channel = channel or self.default_channel
        
        if settings.execution.dry_run:
            logger.info("dry_run_send_message", channel=target_channel, text=text[:100])
            return True
        
        try:
            kwargs = {
                "channel": target_channel,
                "text": text,
            }
            if blocks:
                kwargs["blocks"] = blocks
                
            self.client.chat_postMessage(**kwargs)
            logger.info("message_sent", channel=target_channel)
            return True
        except SlackApiError as e:
            logger.error("slack_send_failed", channel=target_channel, error=str(e))
            return False
    
    def send_error_notification(
        self,
        title: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send an error notification to the errors channel.
        
        Args:
            title: Error title
            error_message: Error message
            details: Additional details
            
        Returns:
            True if successful
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{error_message}```"
                }
            }
        ]
        
        if details:
            detail_text = "\n".join(f"• *{k}:* {v}" for k, v in details.items())
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text
                }
            })
        
        return self.send_message(
            text=f"Error: {title}",
            channel=settings.slack.channel_errors,
            blocks=blocks
        )
    
    def send_agent_update(
        self,
        agent_name: str,
        status: str,
        message: str,
        ticket_id: Optional[str] = None,
        pr_url: Optional[str] = None
    ) -> bool:
        """Send an agent status update.
        
        Args:
            agent_name: Name of the agent
            status: Status (success, in_progress, failed)
            message: Status message
            ticket_id: Optional Jira ticket ID
            pr_url: Optional PR URL
            
        Returns:
            True if successful
        """
        emoji_map = {
            "success": "✅",
            "in_progress": "🔄",
            "failed": "❌",
            "pending": "⏳",
        }
        emoji = emoji_map.get(status, "ℹ️")
        
        text = f"{emoji} *{agent_name}*: {message}"
        
        if ticket_id:
            jira_url = f"{settings.jira.base_url}/browse/{ticket_id}"
            text += f"\n📋 <{jira_url}|{ticket_id}>"
        
        if pr_url:
            text += f"\n🔗 <{pr_url}|View PR>"
        
        return self.send_message(text=text, channel=settings.slack.channel_agents)
    
    def send_approval_request(
        self,
        title: str,
        description: str,
        ticket_id: str,
        pr_url: Optional[str] = None,
        callback_id: Optional[str] = None
    ) -> bool:
        """Send an approval request with interactive buttons.
        
        Args:
            title: Request title
            description: Description of what needs approval
            ticket_id: Related Jira ticket
            pr_url: Related PR URL
            callback_id: Callback ID for button actions
            
        Returns:
            True if successful
        """
        jira_url = f"{settings.jira.base_url}/browse/{ticket_id}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 Approval Required: {title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Ticket:*\n<{jira_url}|{ticket_id}>"
                    },
                ]
            }
        ]
        
        if pr_url:
            blocks[-1]["fields"].append({
                "type": "mrkdwn",
                "text": f"*PR:*\n<{pr_url}|View PR>"
            })
        
        blocks.append({
            "type": "actions",
            "block_id": callback_id or f"approval_{ticket_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "action_id": "approve",
                    "value": ticket_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "action_id": "reject",
                    "value": ticket_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "💬 Request Changes"},
                    "action_id": "request_changes",
                    "value": ticket_id
                }
            ]
        })
        
        return self.send_message(
            text=f"Approval Required: {title}",
            channel=settings.slack.channel_agents,
            blocks=blocks
        )
    
    def get_channel_id(self, channel_name: str) -> Optional[str]:
        """Get channel ID from channel name.
        
        Args:
            channel_name: Channel name (with or without #)
            
        Returns:
            Channel ID or None
        """
        name = channel_name.lstrip("#")
        
        try:
            result = self.client.conversations_list()
            for channel in result["channels"]:
                if channel["name"] == name:
                    return channel["id"]
            return None
        except SlackApiError as e:
            logger.error("slack_channel_lookup_failed", channel=channel_name, error=str(e))
            return None
