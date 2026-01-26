"""
Slack Webhook Routes
Main route handlers for Slack webhooks.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import SLACK_WEBHOOK
from api.webhooks.slack.validation import validate_slack_webhook
from api.webhooks.slack.utils import (
    verify_slack_signature,
    send_slack_immediate_response,
    match_slack_command,
    create_slack_task,
    post_github_comment,
    update_slack_message,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/slack")
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Slack webhook endpoint."""
    channel = None
    task_id = None
    
    try:
        try:
            body = await request.body()
        except Exception as e:
            logger.error("slack_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        try:
            await verify_slack_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("slack_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "slack"
        except json.JSONDecodeError as e:
            logger.error("slack_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("slack_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        
        event = payload.get("event", {})
        channel = event.get("channel", "unknown")
        
        event_type = event.get("type", "unknown")
        
        logger.info("slack_webhook_received", event_type=event_type, channel=channel)
        
        try:
            validation_result = validate_slack_webhook(payload)
            
            if not validation_result.is_valid:
                logger.info(
                    "slack_webhook_rejected_by_validation",
                    event_type=event_type,
                    channel=channel,
                    reason=validation_result.error_message
                )
                return {"status": "rejected", "actions": 0, "message": "Does not meet activation rules"}
        except Exception as e:
            logger.error("slack_webhook_validation_error", error=str(e), event_type=event_type)
        
        try:
            command = match_slack_command(payload, event_type)
            if not command:
                logger.warning("slack_no_command_matched", event_type=event_type, channel=channel)
                return {"status": "received", "actions": 0, "message": "No command matched"}
        except Exception as e:
            logger.error("slack_command_matching_error", error=str(e), channel=channel)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_slack_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("slack_immediate_response_error", error=str(e), channel=channel, command=command.name)
        
        try:
            task_id = await create_slack_task(command, payload, db)
            logger.info("slack_task_created_success", task_id=task_id, channel=channel)
        except Exception as e:
            logger.error("slack_task_creation_failed", error=str(e), error_type=type(e).__name__, channel=channel, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
        try:
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            event_db = WebhookEventDB(
                event_id=event_id,
                webhook_id=SLACK_WEBHOOK.name,
                provider="slack",
                event_type=event_type,
                payload_json=json.dumps(payload),
                matched_command=command.name,
                task_id=task_id,
                response_sent=immediate_response_sent,
                created_at=datetime.now(timezone.utc)
            )
            db.add(event_db)
            await db.commit()
            logger.info("slack_event_logged", event_id=event_id, task_id=task_id, channel=channel)
        except Exception as e:
            logger.error("slack_event_logging_failed", error=str(e), task_id=task_id, channel=channel)
        
        logger.info("slack_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, channel=channel)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "slack_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            channel=channel,
            task_id=task_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slack/interactivity")
async def slack_interactivity(request: Request):
    """
    Handle Slack interactive components (button clicks).
    When Approve/Reject buttons are clicked, post @agent approve/@agent reject to GitHub PR.
    """
    try:
        form_data = await request.form()
        payload_str = form_data.get("payload")

        if not payload_str:
            raise HTTPException(status_code=400, detail="Missing payload")

        payload = json.loads(payload_str)

        body = await request.body()
        await verify_slack_signature(request, body)

        actions = payload.get("actions", [])
        if not actions:
            return {"ok": True}

        action = actions[0]
        action_id = action.get("action_id")
        value_str = action.get("value", "{}")

        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            value = {}

        user = payload.get("user", {})
        user_name = user.get("name", user.get("username", "unknown"))
        channel = payload.get("channel", {}).get("id")
        message_ts = payload.get("message", {}).get("ts")

        repo = value.get("repo")
        pr_number = value.get("pr_number")
        ticket_id = value.get("ticket_id", "N/A")

        if not repo or not pr_number:
            logger.warning("slack_interactivity_missing_pr_info", action_id=action_id)
            return {"ok": True}

        if action_id == "approve_plan":
            comment = f"@agent approve\n\n_Approved via Slack by @{user_name}_"
            success = await post_github_comment(repo, pr_number, comment)

            if success:
                await update_slack_message(
                    channel,
                    message_ts,
                    f"✅ *Plan Approved* by {user_name}\n\n`@agent approve` posted to PR #{pr_number}\nTicket: `{ticket_id}`"
                )
                logger.info("plan_approved_via_slack", repo=repo, pr_number=pr_number, user=user_name)

            return {"ok": True}

        elif action_id == "reject_plan":
            comment = f"@agent reject\n\n_Rejected via Slack by @{user_name}. Please revise the plan._"
            success = await post_github_comment(repo, pr_number, comment)

            if success:
                await update_slack_message(
                    channel,
                    message_ts,
                    f"❌ *Plan Rejected* by {user_name}\n\n`@agent reject` posted to PR #{pr_number}\nTicket: `{ticket_id}`\n\nPlanning agent will revise the plan."
                )
                logger.info("plan_rejected_via_slack", repo=repo, pr_number=pr_number, user=user_name)

            return {"ok": True}

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_interactivity_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
