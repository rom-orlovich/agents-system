"""Dynamic webhook receiver for registered webhooks."""

import hmac
import hashlib
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookConfigDB, WebhookEventDB
from core.webhook_engine import match_commands, execute_command
from core.task_logger import TaskLogger
from core.config import settings

logger = structlog.get_logger()

router = APIRouter()


async def verify_webhook_signature(
    request: Request,
    webhook: WebhookConfigDB,
    provider: str
):
    """Verify webhook HMAC signature based on provider."""
    if not webhook.secret:
        return
    
    body = await request.body()
    
    if provider == "github":
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header:
            raise HTTPException(status_code=401, detail="Missing signature header")
        
        expected = hmac.new(
            webhook.secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(f"sha256={expected}", signature_header):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    elif provider == "jira":
        pass
    
    elif provider == "slack":
        pass
    
    logger.debug("webhook_signature_verified", webhook_id=webhook.webhook_id)


def extract_event_type(request: Request, provider: str, payload: dict) -> str:
    """Extract event type from request based on provider."""
    if provider == "github":
        event = request.headers.get("X-GitHub-Event", "unknown")
        action = payload.get("action", "")
        if action:
            return f"{event}.{action}"
        return event
    
    elif provider == "jira":
        return payload.get("webhookEvent", "unknown")
    
    elif provider == "slack":
        event_type = payload.get("type", "unknown")
        if event_type == "message":
            channel_type = payload.get("channel_type", "channels")
            return f"message.{channel_type}"
        return event_type
    
    else:
        return payload.get("event", "unknown")


@router.post("/{provider}/{webhook_id}")
async def dynamic_webhook_receiver(
    provider: str,
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dynamic webhook receiver that routes to registered webhooks.
    Supports GitHub, Jira, Slack, and custom providers.
    """
    try:
        # 1. Load webhook config from database
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(WebhookConfigDB)
            .options(selectinload(WebhookConfigDB.commands))
            .where(WebhookConfigDB.webhook_id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            logger.warning("webhook_not_found", webhook_id=webhook_id)
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # 2. Check if webhook is enabled
        if not webhook.enabled:
            logger.warning("webhook_disabled", webhook_id=webhook_id)
            raise HTTPException(status_code=403, detail="Webhook is disabled")
        
        # 3. Verify signature if secret configured
        if webhook.secret:
            await verify_webhook_signature(request, webhook, provider)
        
        # 4. Parse payload
        payload = await request.json()
        payload["provider"] = provider
        
        event_type = extract_event_type(request, provider, payload)
        
        logger.info(
            "webhook_received",
            webhook_id=webhook_id,
            provider=provider,
            event_type=event_type
        )

        # Initialize TaskLogger for tracking webhook flow
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task_logger = None
        if settings.task_logs_enabled:
            try:
                task_logger = TaskLogger(task_id, settings.task_logs_dir)

                # Log webhook received stage
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "received",
                    "provider": provider,
                    "event_type": event_type,
                    "webhook_id": webhook_id
                })
            except Exception as e:
                logger.warning("dynamic_webhook_task_logger_init_failed", task_id=task_id, error=str(e))

        # 5. Match event to commands
        matched_commands = match_commands(webhook.commands, event_type, payload)

        # Log command matching stage
        if task_logger:
            try:
                task_logger.append_webhook_event({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "stage": "command_matching",
                    "matched_count": len(matched_commands),
                    "commands": [cmd.command_id for cmd in matched_commands] if matched_commands else []
                })
            except Exception as e:
                logger.warning("dynamic_webhook_command_match_log_failed", task_id=task_id, error=str(e))
        
        if not matched_commands:
            logger.info(
                "no_commands_matched",
                webhook_id=webhook_id,
                event_type=event_type
            )
            
            # Log event even if no commands matched
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            event_db = WebhookEventDB(
                event_id=event_id,
                webhook_id=webhook_id,
                provider=provider,
                event_type=event_type,
                payload_json=json.dumps(payload),
                matched_command=None,
                task_id=None,
                response_sent=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(event_db)
            await db.commit()
            
            return {"status": "received", "actions": 0}
        
        # 6. Execute actions
        results = []
        task_ids = []

        for command in matched_commands:
            result = await execute_command(command, payload, db)
            results.append(result)

            if result.get("task_id"):
                created_task_id = result["task_id"]
                task_ids.append(created_task_id)

                # Initialize TaskLogger for the created task
                if settings.task_logs_enabled:
                    try:
                        from core.webhook_engine import render_template
                        task_logger_for_task = TaskLogger(created_task_id, settings.task_logs_dir)

                        # Log task created stage
                        task_logger_for_task.append_webhook_event({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "stage": "task_created",
                            "task_id": created_task_id,
                            "command": command.command_id,
                            "agent": command.agent
                        })

                        # Write metadata
                        task_logger_for_task.write_metadata({
                            "task_id": created_task_id,
                            "source": "webhook",
                            "provider": provider,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "status": "queued",
                            "assigned_agent": command.agent,
                            "webhook_id": webhook_id
                        })

                        # Render template to get the message
                        rendered_message = render_template(command.template, payload)

                        # Write input
                        task_logger_for_task.write_input({
                            "message": rendered_message,
                            "source_metadata": {
                                "provider": provider,
                                "event_type": event_type,
                                "webhook_id": webhook_id,
                                "command_id": command.command_id
                            }
                        })
                    except Exception as e:
                        logger.warning("dynamic_webhook_task_logger_failed", task_id=created_task_id, error=str(e))
        
        # 7. Log event
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=webhook_id,
            provider=provider,
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=matched_commands[0].command_id if matched_commands else None,
            task_id=task_ids[0] if task_ids else None,
            response_sent=any(r.get("status") == "sent" for r in results),
            created_at=datetime.now(timezone.utc)
        )
        db.add(event_db)
        await db.commit()
        
        logger.info(
            "webhook_processed",
            webhook_id=webhook_id,
            event_id=event_id,
            actions=len(results),
            task_ids=task_ids
        )
        
        return {
            "status": "processed",
            "event_id": event_id,
            "actions": len(results),
            "task_ids": task_ids
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "webhook_receiver_error",
            error=str(e),
            webhook_id=webhook_id,
            provider=provider
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{provider}/{webhook_id}/events")
async def list_webhook_events(
    provider: str,
    webhook_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """List recent events for a webhook."""
    try:
        result = await db.execute(
            select(WebhookEventDB)
            .where(WebhookEventDB.webhook_id == webhook_id)
            .order_by(WebhookEventDB.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "matched_command": event.matched_command,
                "task_id": event.task_id,
                "response_sent": event.response_sent,
                "created_at": event.created_at.isoformat()
            }
            for event in events
        ]
    except Exception as e:
        logger.error("list_events_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
