import uuid
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Callable
from core.models import (
    WebhookResponse,
    TaskQueueMessage,
    GitHubWebhookPayload,
    WebhookProvider,
)
from core.task_logger import TaskLogger
from queue.redis_queue import TaskQueue
from webhooks.signature_validator import GitHubSignatureValidator

logger = structlog.get_logger()


class GitHubWebhookHandler:
    def __init__(
        self,
        task_queue: TaskQueue,
        logs_base_dir: Path | None = None,
        signature_secret: str | None = None,
    ):
        self.task_queue = task_queue
        self.logs_base_dir = logs_base_dir or Path("/data/logs/tasks")
        self.signature_validator: Callable[[bytes, str], bool] | None = None

        if signature_secret:
            validator = GitHubSignatureValidator(signature_secret)
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
                "provider": WebhookProvider.GITHUB.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "initializing",
            }
        )

        task_logger.log_webhook_event(
            stage="received", provider=WebhookProvider.GITHUB.value, headers=headers
        )

        if self.signature_validator and "X-Hub-Signature-256" in headers:
            import json

            payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
            signature = headers["X-Hub-Signature-256"]

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
            validated_payload = GitHubWebhookPayload.model_validate(payload)
        except Exception as e:
            task_logger.log_webhook_event(
                stage="parsing", status="failed", error=str(e)
            )
            return WebhookResponse(
                success=False,
                task_id=None,
                message="Payload validation failed",
                error=f"Invalid payload for GitHub: {str(e)}",
            )

        task_logger.log_webhook_event(stage="parsing", status="completed")

        input_message = self._extract_message(validated_payload)

        if not input_message or not self._has_command(input_message):
            task_logger.log_webhook_event(stage="command_matching", status="no_match")
            return WebhookResponse(
                success=True,
                task_id=None,
                message="No command found in webhook",
                error=None,
            )

        task_logger.write_input(
            {
                "message": input_message,
                "source_metadata": {
                    "provider": WebhookProvider.GITHUB.value,
                    "action": validated_payload.action,
                    "repository": str(
                        validated_payload.repository.get("full_name", "")
                    ),
                },
            }
        )

        task_logger.log_webhook_event(stage="command_matching", status="matched")

        task = TaskQueueMessage(
            task_id=task_id,
            session_id=f"session-{uuid.uuid4().hex[:12]}",
            user_id=str(validated_payload.sender.get("login", "unknown")),
            input_message=input_message,
            agent_type="planning",
            model="claude-3-opus",
            source_metadata={
                "provider": WebhookProvider.GITHUB.value,
                "action": validated_payload.action,
                "repository": str(validated_payload.repository.get("full_name", "")),
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
                "provider": WebhookProvider.GITHUB.value,
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

    def _extract_message(self, payload: GitHubWebhookPayload) -> str:
        if payload.comment and isinstance(payload.comment, dict):
            return str(payload.comment.get("body", ""))
        if payload.issue and isinstance(payload.issue, dict):
            return str(payload.issue.get("body", ""))
        if payload.pull_request and isinstance(payload.pull_request, dict):
            return str(payload.pull_request.get("body", ""))
        return ""

    def _has_command(self, message: str) -> bool:
        return "@agent" in message.lower()
