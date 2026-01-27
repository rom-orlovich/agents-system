"""
Notification configuration.

Provides configuration for Slack notification channels and settings.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationConfig:
    """
    Configuration for task notifications.

    Attributes:
        enabled: Whether notifications are enabled
        success_channel: Channel for successful task notifications
        error_channel: Channel for failed task notifications
        override_channel: Optional channel to override both
    """
    enabled: bool = True
    success_channel: str = "#ai-agent-activity"
    error_channel: str = "#ai-agent-errors"
    override_channel: Optional[str] = None

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """
        Create config from environment variables.

        Environment variables:
        - SLACK_NOTIFICATIONS_ENABLED: "true" or "false"
        - SLACK_CHANNEL_AGENTS: Channel for success notifications
        - SLACK_CHANNEL_ERRORS: Channel for error notifications
        """
        enabled_str = os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true")
        enabled = enabled_str.lower() == "true"

        return cls(
            enabled=enabled,
            success_channel=os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity"),
            error_channel=os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors"),
            override_channel=os.getenv("SLACK_NOTIFICATION_CHANNEL"),
        )

    def get_channel(self, success: bool) -> str:
        """
        Get the appropriate channel for a notification.

        Args:
            success: Whether the task succeeded

        Returns:
            Channel name to use
        """
        if self.override_channel:
            return self.override_channel
        return self.success_channel if success else self.error_channel
