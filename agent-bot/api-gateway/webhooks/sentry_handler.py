import uuid
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Callable
from core.models import (
    WebhookResponse,
    TaskQueueMessage,
    SentryWebhookPayload,
    WebhookProvider,
)
from core.task_logger import TaskLogger
from queue.redis_queue import TaskQueue
from webhooks.signature_validator import SentrySignatureValidator
from webhooks.config import WebhookConfig, create_default_sentry_config

logger = structlog.get_logger()


class SentryWebhookHandler:
    def __init__(
        self,
        task_queue: TaskQueue,
        logs_base_dir: Path | None = None,
        signature_secret: str | None = None,
        webhook_config: WebhookConfig | None = None,
    ):
        self.task_queue = task_queue
        self.logs_base_dir = logs_base_dir or Path("/data/logs/tasks")
        self.webhook_config = webhook_config or create_default_sentry_config()
        self.signature_validator: Callable[[bytes, str], bool] | None = None

        if signature_secret:
            validator = SentrySignatureValidator(signature_secret)
            self.signature_validator = validator.validate

    async def handle(
        self, payload: Dict[str, Any], headers: Dict[str, str]
    ) -> WebhookResponse:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task_logger = TaskLogger.get_or_create(task_id, self.logs_base_dir)

        task_logger.write_metadata(
            {
                "task_id": task_id,
                "source": "webhook",
                "provider": WebhookProvider.SENTRY.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "initializing",
            }
        )

        task_logger.log_webhook_event(
            stage="received", provider=WebhookProvider.SENTRY.value, headers=headers
        )

        if self.signature_validator and "Sentry-Hook-Signature" in headers:
            import json

            payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
            signature = headers["Sentry-Hook-Signature"]

            if not self.signature_validator(payload_bytes, signature):
                task_logger.log_webhook_event(
                    stage="validation", status="failed", error="Invalid signature"
                )
                return WebhookResponse(
                    success=False,
                    task_id=None,
                    message="Signature validation failed",
                    error="Invalid signature",
                )

        task_logger.log_webhook_event(stage="parsing", status="started")

        try:
            validated_payload = SentryWebhookPayload.model_validate(payload)
        except Exception as e:
            task_logger.log_webhook_event(
                stage="parsing", status="failed", error=str(e)
            )
            return WebhookResponse(
                success=False,
                task_id=None,
                message="Payload validation failed",
                error=f"Invalid payload for Sentry: {str(e)}",
            )

        task_logger.log_webhook_event(stage="parsing", status="completed")

        input_message = self._extract_message(validated_payload)

        if not input_message:
            task_logger.log_webhook_event(stage="command_matching", status="no_message")
            return WebhookResponse(
                success=True,
                task_id=None,
                message="No message found in webhook",
                error=None,
            )

        command_config = self.webhook_config.match_command(input_message)
        if not command_config:
            task_logger.log_webhook_event(stage="command_matching", status="no_match")
            return WebhookResponse(
                success=True,
                task_id=None,
                message="No command found in webhook",
                error=None,
            )

        data = validated_payload.data
        issue_id = str(data.get("id", "unknown"))
        project = data.get("project", {})
        if isinstance(project, dict):
            project_name = str(project.get("name", "unknown"))
        else:
            project_name = "unknown"

        actor = validated_payload.actor or {}
        user_id = str(actor.get("name", "sentry-system"))

        task_logger.write_input(
            {
                "message": input_message,
                "source_metadata": {
                    "provider": WebhookProvider.SENTRY.value,
                    "action": validated_payload.action,
                    "issue_id": issue_id,
                    "project": project_name,
                },
            }
        )

        task_logger.log_webhook_event(stage="command_matching", status="matched")

        task = TaskQueueMessage(
            task_id=task_id,
            session_id=f"session-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            input_message=input_message,
            agent_type=command_config.agent_name,
            model=command_config.model.value,
            source_metadata={
                "provider": WebhookProvider.SENTRY.value,
                "action": validated_payload.action,
                "issue_id": issue_id,
                "project": project_name,
            },
        )

        task_logger.log_webhook_event(
            stage="task_created",
            status="completed",
            task_id=task.task_id,
            agent=task.agent_type,
        )

        task_logger.write_metadata(
            {
                "task_id": task_id,
                "source": "webhook",
                "provider": WebhookProvider.SENTRY.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "queued",
                "assigned_agent": task.agent_type,
                "model": task.model,
            }
        )

        task_logger.log_queue_event(stage="queue_push", status="started")
        await self.task_queue.enqueue(task)
        task_logger.log_queue_event(
            stage="queue_push", status="completed", queue_name="tasks"
        )

        return WebhookResponse(
            success=True,
            task_id=task_id,
            message="Task created and queued",
            error=None,
        )

    def _extract_message(self, payload: SentryWebhookPayload) -> str:
        data = payload.data

        issue = data.get("issue", {})
        if isinstance(issue, dict):
            title = issue.get("title", "")
            if title:
                culprit = issue.get("culprit", "")
                metadata = issue.get("metadata", {})

                if isinstance(metadata, dict):
                    error_type = metadata.get("type", "")
                    error_value = metadata.get("value", "")

                    message_parts = [f"Sentry Error: {title}"]
                    if error_type:
                        message_parts.append(f"Type: {error_type}")
                    if error_value:
                        message_parts.append(f"Value: {error_value}")
                    if culprit:
                        message_parts.append(f"Location: {culprit}")

                    return " | ".join(message_parts)

                return f"Sentry Error: {title}"

        return ""
