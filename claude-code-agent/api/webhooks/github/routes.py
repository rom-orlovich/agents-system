from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog
from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import GITHUB_WEBHOOK
from core.task_logger import TaskLogger
from core.config import settings
from api.webhooks.github.utils import (
    send_slack_notification,
)
from api.webhooks.github.handlers import handle_github_task_completion, GitHubWebhookHandler
from pathlib import Path
from api.webhooks.github.constants import (
    PROVIDER_NAME,
    EVENT_HEADER,
    DEFAULT_EVENT_TYPE,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_RECEIVED,
    MESSAGE_DOES_NOT_MEET_RULES,
    MESSAGE_NO_COMMAND_MATCHED,
    MESSAGE_TASK_QUEUED,
    MESSAGE_IMMEDIATE_RESPONSE_FAILED,
    ERROR_IMMEDIATE_RESPONSE_FAILED,
)

from api.webhooks.common.utils import load_webhook_config_from_yaml

logger = structlog.get_logger()
router = APIRouter()

GITHUB_CONFIG = load_webhook_config_from_yaml(Path(__file__).parent / "config.yaml")
COMPLETION_HANDLER = "api.webhooks.github.handlers.handle_github_task_completion"
webhook_handler = GitHubWebhookHandler(GITHUB_CONFIG)


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    GitHub webhook endpoint.
    
    Flow:
    1. Get webhook event
    2. Validate webhook
    3. Validate command
    4. Send immediate response (reaction/comment)
    5. Create task (with completion handler registered: handle_github_task_completion)
    6. Put task in queue
    7. Log event
    8. Send back HTTP response
    
    After task completes (task worker calls handle_github_task_completion):
    - handle_github_task_completion() posts comment to GitHub PR/issue
    - handle_github_task_completion() sends Slack notification (if enabled)
    - Task worker updates conversation with result
    """
    repo_info = None
    issue_number = None
    task_id = None
    
    try:
        body = await request.body()

        await webhook_handler.verify_signature(request, body)

        if GITHUB_CONFIG is None:
            logger.error("github_webhook_config_not_loaded")
            raise HTTPException(
                status_code=503,
                detail="GitHub webhook configuration not loaded"
            )

        payload = webhook_handler.parse_payload(body, PROVIDER_NAME)
        
        repo = payload.get("repository", {})
        repo_info = f"{repo.get('owner', {}).get('login', 'unknown')}/{repo.get('name', 'unknown')}"
        issue = payload.get("issue") or payload.get("pull_request")
        if issue:
            issue_number = issue.get("number")
        
        event_type = request.headers.get(EVENT_HEADER, DEFAULT_EVENT_TYPE)
        action = payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"
        
        logger.info(
            "github_webhook_received",
            event_type=event_type,
            action=payload.get("action"),
            repo=repo_info,
            issue_number=issue_number,
            comment_id=payload.get("comment", {}).get("id"),
            comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
        )

        task_id = f"task-{uuid.uuid4().hex[:12]}"

        task_logger = None
        if settings.task_logs_enabled:
            try:
                task_logger = TaskLogger(task_id, settings.task_logs_dir)

                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "received",
                    "event_type": event_type,
                    "action": payload.get("action"),
                    "repo": repo_info,
                    "issue_number": issue_number,
                    "comment_id": payload.get("comment", {}).get("id")
                })
            except Exception as e:
                logger.warning("github_task_logger_init_failed", task_id=task_id, error=str(e))
        
        validation_result = await webhook_handler.validate_webhook(payload)

        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "validation",
                    "status": "passed" if validation_result.is_valid else "failed",
                    "reason": validation_result.error_message if not validation_result.is_valid else None
                })
            except Exception as e:
                logger.warning("github_validation_log_failed", task_id=task_id, error=str(e))

        if not validation_result.is_valid:
            logger.info(
                "github_webhook_rejected_by_validation",
                event_type=event_type,
                action=payload.get("action"),
                repo=repo_info,
                issue_number=issue_number,
                reason=validation_result.error_message,
                comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
            )
            return {"status": STATUS_REJECTED, "actions": 0, "message": MESSAGE_DOES_NOT_MEET_RULES}
        
        command = await webhook_handler.match_command(payload)

        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "command_matching",
                    "command": command.name if command else None,
                    "matched": bool(command)
                })
            except Exception as e:
                logger.warning("github_command_match_log_failed", task_id=task_id, error=str(e))

        if not command:
            logger.warning(
                "github_no_command_matched",
                event_type=event_type,
                action=payload.get("action"),
                repo=repo_info,
                issue_number=issue_number,
                comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
            )
            return {"status": STATUS_RECEIVED, "actions": 0, "message": MESSAGE_NO_COMMAND_MATCHED}
        
        immediate_response_sent = await webhook_handler.send_immediate_response(payload, command, event_type)

        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "immediate_response",
                    "action": command.immediate_response if command else None,
                    "success": immediate_response_sent
                })
            except Exception as e:
                logger.warning("github_immediate_response_log_failed", task_id=task_id, error=str(e))

        if not immediate_response_sent:
            logger.error(
                "github_immediate_response_failed",
                repo=repo_info,
                issue_number=issue_number,
                event_type=event_type,
                message="Immediate response failed - webhook rejected"
            )
            return {
                "status": STATUS_REJECTED,
                "message": MESSAGE_IMMEDIATE_RESPONSE_FAILED,
                "error": ERROR_IMMEDIATE_RESPONSE_FAILED
            }

        actual_task_id = await webhook_handler.create_task(command, payload, db, COMPLETION_HANDLER)
        logger.info("github_task_created_success", task_id=actual_task_id, repo=repo_info, issue_number=issue_number)

        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "task_created",
                    "task_id": actual_task_id,
                    "agent": command.agent_type,
                    "command": command.name
                })

                task_logger.write_metadata({
                    "task_id": actual_task_id,
                    "source": "webhook",
                    "provider": PROVIDER_NAME,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "queued",
                    "assigned_agent": command.agent_type,
                    "command": command.name
                })

                comment_body = payload.get("comment", {}).get("body", "")
                task_logger.write_input({
                    "message": command.generate_input_message(payload),
                    "source_metadata": {
                        "provider": PROVIDER_NAME,
                        "event_type": event_type,
                        "repo": repo_info,
                        "issue_number": issue_number,
                        "comment_id": payload.get("comment", {}).get("id"),
                        "comment_body": comment_body[:500] if comment_body else None,
                        "webhook_id": GITHUB_WEBHOOK.name
                    }
                })
            except Exception as e:
                logger.warning("github_task_creation_log_failed", task_id=actual_task_id, error=str(e))
        
        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "queue_push",
                    "task_id": actual_task_id,
                    "status": "queued"
                })
            except Exception as e:
                logger.warning("github_queue_push_log_failed", task_id=actual_task_id, error=str(e))

        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,
            provider=PROVIDER_NAME,
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=actual_task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.now(timezone.utc)
        )
        db.add(event_db)
        await db.commit()
        logger.info("github_event_logged", event_id=event_id, task_id=actual_task_id, repo=repo_info, issue_number=issue_number)

        logger.info(
            "github_completion_handler_registered",
            task_id=actual_task_id,
            handler=COMPLETION_HANDLER,
            message="Completion handler registered - will be called by task worker when task completes"
        )

        logger.info(
            "github_webhook_processed",
            task_id=actual_task_id,
            command=command.name,
            event_type=event_type,
            repo=repo_info,
            issue_number=issue_number,
            immediate_response_sent=immediate_response_sent
        )

        return {
            "status": STATUS_ACCEPTED,
            "task_id": actual_task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER,
            "message": MESSAGE_TASK_QUEUED
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "github_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
