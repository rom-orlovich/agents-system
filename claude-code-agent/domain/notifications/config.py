import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationConfig:
    enabled: bool = True
    success_channel: str = "#ai-agent-activity"
    error_channel: str = "#ai-agent-errors"
    override_channel: Optional[str] = None

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        enabled_str = os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true")
        enabled = enabled_str.lower() == "true"

        return cls(
            enabled=enabled,
            success_channel=os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity"),
            error_channel=os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors"),
            override_channel=os.getenv("SLACK_NOTIFICATION_CHANNEL"),
        )

    def get_channel(self, success: bool) -> str:
        if self.override_channel:
            return self.override_channel
        return self.success_channel if success else self.error_channel
