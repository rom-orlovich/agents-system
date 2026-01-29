from fastapi import Request, HTTPException, status
import structlog
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os
from core.task_logger import TaskLogger
from core.models import (
    WebhookResponse,
    TaskQueueMessage,
    WebhookProvider,
    GitHubWebhookPayload,
    JiraWebhookPayload,
    SlackWebhookPayload,
    SentryWebhookPayload,
)
from queue.redis_queue import TaskQueue

logger = structlog.get_logger()


class WebhookReceiver:
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue

    async def receive_github_webhook(self, request: Request) -> WebhookResponse:
        return await self._receive_webhook(request, WebhookProvider.GITHUB)

    async def receive_jira_webhook(self, request: Request) -> WebhookResponse:
        return await self._receive_webhook(request, WebhookProvider.JIRA)

    async def receive_slack_webhook(self, request: Request) -> WebhookResponse:
        return await self._receive_webhook(request, WebhookProvider.SLACK)

    async def receive_sentry_webhook(self, request: Request) -> WebhookResponse:
        return await self._receive_webhook(request, WebhookProvider.SENTRY)

    async def _receive_webhook(
        self, request: Request, provider: WebhookProvider
    ) -> WebhookResponse:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        logs_base_dir = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
        task_logger = TaskLogger.get_or_create(task_id, logs_base_dir)

        task_logger.write_metadata(
            {
                "task_id": task_id,
                "source": "webhook",
                "provider": provider.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "initializing",
            }
        )

        task_logger.log_webhook_event(
            stage="received",
            provider=provider.value,
            headers=dict(request.headers),
        )

        task_logger.log_webhook_event(stage="parsing", status="started")
        try:
            payload = await request.json()
        except Exception as e:
            task_logger.log_webhook_event(
                stage="parsing", status="failed", error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON payload: {str(e)}",
            )

        task_logger.log_webhook_event(
            stage="parsing", status="completed", payload_size=len(str(payload))
        )

        validated_payload = self._validate_payload(payload, provider, task_logger)

        if validated_payload is None:
            return WebhookResponse(
                success=True, task_id=None, message="No action required", error=None
            )

        input_message = self._extract_message(validated_payload, provider)

        if not input_message:
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
                    "provider": provider.value,
                    **self._extract_source_metadata(validated_payload, provider),
                },
            }
        )

        task_logger.log_webhook_event(stage="command_matching", status="matched")

        task = TaskQueueMessage(
            task_id=task_id,
            session_id=f"session-{uuid.uuid4().hex[:12]}",
            user_id=self._extract_user_id(validated_payload, provider),
            input_message=input_message,
            agent_type="planning",
            model="claude-3-opus",
            source_metadata=self._extract_source_metadata(validated_payload, provider),
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
                "provider": provider.value,
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

    def _validate_payload(
        self,
        payload: dict,
        provider: WebhookProvider,
        task_logger: TaskLogger,
    ) -> (
        GitHubWebhookPayload
        | JiraWebhookPayload
        | SlackWebhookPayload
        | SentryWebhookPayload
        | None
    ):
        task_logger.log_webhook_event(stage="validation", status="started")
        try:
            if provider == WebhookProvider.GITHUB:
                validated = GitHubWebhookPayload.model_validate(payload)
            elif provider == WebhookProvider.JIRA:
                validated = JiraWebhookPayload.model_validate(payload)
            elif provider == WebhookProvider.SLACK:
                validated = SlackWebhookPayload.model_validate(payload)
            elif provider == WebhookProvider.SENTRY:
                validated = SentryWebhookPayload.model_validate(payload)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            task_logger.log_webhook_event(stage="validation", status="passed")
            return validated
        except Exception as e:
            task_logger.log_webhook_event(
                stage="validation", status="failed", error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload for {provider.value}: {str(e)}",
            )

    def _extract_message(
        self,
        payload: (
            GitHubWebhookPayload
            | JiraWebhookPayload
            | SlackWebhookPayload
            | SentryWebhookPayload
        ),
        provider: WebhookProvider,
    ) -> str:
        if provider == WebhookProvider.GITHUB:
            if isinstance(payload, GitHubWebhookPayload):
                if payload.comment and isinstance(payload.comment, dict):
                    return str(payload.comment.get("body", ""))
                if payload.issue and isinstance(payload.issue, dict):
                    return str(payload.issue.get("body", ""))
                if payload.pull_request and isinstance(payload.pull_request, dict):
                    return str(payload.pull_request.get("body", ""))
        elif provider == WebhookProvider.JIRA:
            if isinstance(payload, JiraWebhookPayload):
                if payload.comment and isinstance(payload.comment, dict):
                    return str(payload.comment.get("body", ""))
                if payload.issue and isinstance(payload.issue, dict):
                    issue_fields = payload.issue.get("fields", {})
                    if isinstance(issue_fields, dict):
                        return str(issue_fields.get("description", ""))
        elif provider == WebhookProvider.SLACK:
            if isinstance(payload, SlackWebhookPayload):
                if payload.event and isinstance(payload.event, dict):
                    return str(payload.event.get("text", ""))
        elif provider == WebhookProvider.SENTRY:
            if isinstance(payload, SentryWebhookPayload):
                if payload.data and isinstance(payload.data, dict):
                    issue = payload.data.get("issue", {})
                    if isinstance(issue, dict):
                        return str(issue.get("title", ""))
        return ""

    def _extract_user_id(
        self,
        payload: (
            GitHubWebhookPayload
            | JiraWebhookPayload
            | SlackWebhookPayload
            | SentryWebhookPayload
        ),
        provider: WebhookProvider,
    ) -> str:
        if provider == WebhookProvider.GITHUB:
            if isinstance(payload, GitHubWebhookPayload):
                sender = payload.sender
                if isinstance(sender, dict):
                    return str(sender.get("login", "unknown"))
        elif provider == WebhookProvider.JIRA:
            if isinstance(payload, JiraWebhookPayload):
                if payload.user and isinstance(payload.user, dict):
                    return str(payload.user.get("accountId", "unknown"))
        elif provider == WebhookProvider.SLACK:
            if isinstance(payload, SlackWebhookPayload):
                if payload.event and isinstance(payload.event, dict):
                    return str(payload.event.get("user", "unknown"))
        elif provider == WebhookProvider.SENTRY:
            if isinstance(payload, SentryWebhookPayload):
                if payload.actor and isinstance(payload.actor, dict):
                    return str(payload.actor.get("name", "unknown"))
        return "unknown"

    def _extract_source_metadata(
        self,
        payload: (
            GitHubWebhookPayload
            | JiraWebhookPayload
            | SlackWebhookPayload
            | SentryWebhookPayload
        ),
        provider: WebhookProvider,
    ) -> dict[str, str | int | bool]:
        metadata: dict[str, str | int | bool] = {}

        if provider == WebhookProvider.GITHUB:
            if isinstance(payload, GitHubWebhookPayload):
                metadata["action"] = payload.action
                repo = payload.repository
                if isinstance(repo, dict):
                    metadata["repository"] = str(repo.get("full_name", ""))
        elif provider == WebhookProvider.JIRA:
            if isinstance(payload, JiraWebhookPayload):
                metadata["event"] = payload.webhookEvent
                issue = payload.issue
                if isinstance(issue, dict):
                    metadata["issue_key"] = str(issue.get("key", ""))
        elif provider == WebhookProvider.SLACK:
            if isinstance(payload, SlackWebhookPayload):
                metadata["type"] = payload.type
        elif provider == WebhookProvider.SENTRY:
            if isinstance(payload, SentryWebhookPayload):
                metadata["action"] = payload.action

        return metadata
