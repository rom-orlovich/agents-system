import structlog
from typing import Any, Optional, Protocol

from domain.models.notifications import TaskNotification
from domain.notifications.config import NotificationConfig
from domain.notifications.builder import NotificationBuilder

logger = structlog.get_logger()


class SlackClientProtocol(Protocol):

    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list] = None,
        **kwargs: Any,
    ) -> dict:
        ...


class NotificationService:

    def __init__(
        self,
        slack_client: SlackClientProtocol,
        config: Optional[NotificationConfig] = None,
    ):
        self.client = slack_client
        self.config = config or NotificationConfig.from_env()

    async def send(
        self,
        notification: TaskNotification,
        requires_approval: bool = False,
        override_channel: Optional[str] = None,
    ) -> bool:
        if not self.config.enabled:
            logger.debug(
                "notification_disabled",
                task_id=notification.task_id,
            )
            return False

        channel = (
            override_channel
            or notification.routing.get("slack_channel") if notification.routing else None
            or self.config.get_channel(notification.success)
        )

        blocks = NotificationBuilder.build_blocks(notification)

        if requires_approval and notification.routing:
            from domain.models.routing import RoutingMetadata
            routing = RoutingMetadata(
                repo=notification.routing.get("repo"),
                pr_number=notification.routing.get("pr_number"),
                ticket_key=notification.routing.get("ticket_key"),
            )
            approval_blocks = NotificationBuilder.build_approval_buttons(
                task_id=notification.task_id,
                command=notification.command,
                routing=routing,
                source=notification.source.value,
            )
            blocks.extend(approval_blocks)

        text = notification.get_summary_text()

        try:
            await self.client.post_message(
                channel=channel,
                text=text,
                blocks=blocks,
            )

            logger.info(
                "notification_sent",
                task_id=notification.task_id,
                source=notification.source.value,
                channel=channel,
                success=notification.success,
            )
            return True

        except Exception as e:
            error_msg = str(e).lower()

            if "channel_not_found" in error_msg:
                env_var = (
                    "SLACK_CHANNEL_AGENTS"
                    if notification.success
                    else "SLACK_CHANNEL_ERRORS"
                )
                logger.warning(
                    "notification_channel_not_found",
                    task_id=notification.task_id,
                    channel=channel,
                    message=f"Channel does not exist. Set {env_var} to a valid channel.",
                )
            else:
                logger.error(
                    "notification_failed",
                    task_id=notification.task_id,
                    channel=channel,
                    error=str(e),
                )

            return False

    async def send_task_completion(
        self,
        task_id: str,
        webhook_source: str,
        command: str,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        pr_url: Optional[str] = None,
        cost_usd: float = 0.0,
        user_request: Optional[str] = None,
        ticket_key: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> bool:
        from domain.models.webhook_payload import WebhookSource

        try:
            source = WebhookSource(webhook_source.lower())
        except ValueError:
            source = WebhookSource.SLACK

        routing = None
        if payload:
            routing = payload.get("routing", {})

        notification = TaskNotification(
            task_id=task_id,
            source=source,
            command=command,
            success=success,
            result=result,
            error=error,
            pr_url=pr_url,
            cost_usd=cost_usd,
            user_request=user_request,
            ticket_key=ticket_key,
            routing=routing,
        )

        return await self.send(notification)


_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _notification_service

    if _notification_service is None:
        from core.slack_client import slack_client

        _notification_service = NotificationService(
            slack_client=slack_client,
            config=NotificationConfig.from_env(),
        )

    return _notification_service
