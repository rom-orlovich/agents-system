from fastapi import APIRouter, Request, HTTPException, status
from datetime import datetime, timezone
import structlog
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.ports.queue import TaskQueueMessage, TaskPriority, QueuePort
from webhooks.registry.registry import WebhookRegistry
from webhooks.registry.protocol import PayloadParseError

logger = structlog.get_logger()


def create_webhook_router(
    registry: WebhookRegistry,
    queue: QueuePort,
) -> APIRouter:
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/{provider}")
    async def handle_webhook(provider: str, request: Request):
        if not registry.has_handler(provider):
            logger.warning("webhook_provider_not_found", provider=provider)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider} not supported",
            )

        handler = registry.get_handler(provider)
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Handler registration error",
            )

        body = await request.body()
        headers = dict(request.headers)

        secret = request.headers.get("x-webhook-secret", "")

        try:
            is_valid = await handler.validate(body, headers, secret)
            if not is_valid:
                logger.warning(
                    "webhook_validation_failed",
                    provider=provider,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )
        except Exception as e:
            logger.error(
                "webhook_validation_error",
                provider=provider,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}",
            )

        try:
            payload = await handler.parse(body, headers)
        except PayloadParseError as e:
            logger.error(
                "webhook_parse_error",
                provider=provider,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parse error: {str(e)}",
            )

        should_process = await handler.should_process(payload)
        if not should_process:
            logger.info(
                "webhook_skipped",
                provider=provider,
                event=payload.event_type,
            )
            return {"status": "ignored", "event": payload.event_type}

        task_request = await handler.create_task_request(payload)

        task_message = TaskQueueMessage(
            task_id=f"task-{datetime.now(timezone.utc).timestamp()}",
            installation_id=task_request.installation_id,
            provider=task_request.provider,
            input_message=task_request.input_message,
            priority=TaskPriority(task_request.priority),
            source_metadata=task_request.source_metadata,
            created_at=datetime.now(timezone.utc),
        )

        await queue.enqueue(task_message)

        logger.info(
            "webhook_processed",
            provider=provider,
            event=payload.event_type,
            task_id=task_message.task_id,
        )

        return {
            "status": "accepted",
            "task_id": task_message.task_id,
            "event": payload.event_type,
        }

    @router.get("/health")
    async def health():
        return {
            "status": "healthy",
            "providers": registry.list_providers(),
        }

    return router
