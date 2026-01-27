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
    post_slack_task_comment,
    send_slack_notification,
    create_task_from_button_action,
)

logger = structlog.get_logger()
router = APIRouter()

COMPLETION_HANDLER = "api.webhooks.slack.routes.handle_slack_task_completion"


async def handle_slack_task_completion(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    task_id: str = None,
    command: str = None,
    result: str = None,
    error: str = None
) -> bool:
    """
    Handle Slack task completion callback.
    
    Called by task worker when task completes.
    
    Actions:
    1. Extract routing metadata and task summary
    2. Build Block Kit message with rich formatting
    3. Post message to Slack thread with task result
    4. Send Slack notification (if enabled)
    
    Returns:
        True if message posted successfully, False otherwise
    """
    from api.webhooks.slack.utils import extract_task_summary, build_task_completion_blocks
    from core.webhook_configs import SLACK_WEBHOOK
    
    # Extract routing from payload
    event = payload.get("event", {})
    routing = {
        "channel": event.get("channel"),
        "thread_ts": event.get("ts"),
        "repo": payload.get("routing", {}).get("repo"),
        "pr_number": payload.get("routing", {}).get("pr_number"),
        "ticket_key": payload.get("routing", {}).get("ticket_key")
    }
    
    # Extract task summary from result
    task_metadata = {
        "classification": payload.get("classification", "SIMPLE")
    }
    summary = extract_task_summary(result or message, task_metadata)
    
    # Determine if buttons are needed
    # Check if command requires approval
    requires_approval = False
    if command:
        for cmd in SLACK_WEBHOOK.commands:
            if cmd.name == command:
                requires_approval = cmd.requires_approval
                break
    
    # Build Block Kit blocks
    blocks = build_task_completion_blocks(
        summary=summary,
        routing=routing,
        requires_approval=requires_approval,
        task_id=task_id or "unknown",
        cost_usd=cost_usd,
        command=command or "",
        source=payload.get("routing", {}).get("source", "slack")
    )
    
    # Post message with Block Kit blocks
    formatted_message = error if not success and error else message
    
    comment_posted = await post_slack_task_comment(
        payload=payload,
        message=formatted_message,
        success=success,
        cost_usd=cost_usd,
        blocks=blocks
    )
    
    await send_slack_notification(
        task_id=task_id,
        webhook_source="slack",
        command=command,
        success=success,
        result=result,
        error=error
    )
    
    return comment_posted


@router.post("/slack")
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Slack webhook endpoint.
    
    Flow:
    1. Get webhook event
    2. Validate webhook
    3. Validate command
    4. Send immediate response (ephemeral message)
    5. Create task (with completion handler registered: handle_slack_task_completion)
    6. Put task in queue
    7. Log event
    8. Send back HTTP response
    
    After task completes (task worker calls handle_slack_task_completion):
    - handle_slack_task_completion() posts message to Slack thread
    - handle_slack_task_completion() sends Slack notification (if enabled)
    - Task worker updates conversation with result
    """
    channel = None
    task_id = None
    
    try:
        try:
            body = await request.body()
        except Exception as e:
            logger.error("slack_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
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
            challenge = payload.get("challenge")
            logger.info("slack_url_verification_challenge", challenge=challenge)
            return {"challenge": challenge}
        
        try:
            await verify_slack_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("slack_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
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
            command = await match_slack_command(payload, event_type)
            if not command:
                logger.warning("slack_no_command_matched", event_type=event_type, channel=channel)
                return {"status": "received", "actions": 0, "message": "No command matched"}
        except Exception as e:
            logger.error("slack_command_matching_error", error=str(e), channel=channel)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        immediate_response_sent = await send_slack_immediate_response(payload, command, event_type)
        
        task_id = await create_slack_task(command, payload, db, completion_handler=COMPLETION_HANDLER)
        logger.info("slack_task_created_success", task_id=task_id, channel=channel)
        
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
        
        logger.info(
            "slack_completion_handler_registered",
            task_id=task_id,
            handler=COMPLETION_HANDLER,
            message="Completion handler will be called by task worker when task completes"
        )
        
        logger.info("slack_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, channel=channel)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER
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
async def slack_interactivity(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    Handle Slack interactive components (button clicks).
    When Approve/Review/Reject buttons are clicked, create new tasks routed to GitHub PR, Jira ticket, or Slack.
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

        # Handle legacy approve_plan and reject_plan actions (backward compatibility)
        if action_id == "approve_plan":
            repo = value.get("repo")
            pr_number = value.get("pr_number")
            ticket_id = value.get("ticket_id", "N/A")
            
            if repo and pr_number:
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
            repo = value.get("repo")
            pr_number = value.get("pr_number")
            ticket_id = value.get("ticket_id", "N/A")
            
            if repo and pr_number:
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
        
        # Handle new approve_task, review_task, reject_task actions
        if action_id in ["approve_task", "review_task", "reject_task"]:
            action_type = value.get("action")
            original_task_id = value.get("original_task_id", "unknown")
            command = value.get("command", "unknown")
            source = value.get("source", "slack")
            routing = value.get("routing", {})
            
            if not action_type:
                logger.warning("slack_interactivity_missing_action", action_id=action_id)
                return {"ok": True}
            
            # Create task from button action
            task_id = await create_task_from_button_action(
                action=action_type,
                routing=routing,
                source=source,
                original_task_id=original_task_id,
                command=command,
                db=db,
                user_name=user_name
            )
            
            if task_id:
                # Update message to show action taken
                action_emoji = {
                    "approve": "✅",
                    "review": "👀",
                    "reject": "❌"
                }.get(action_type, "⚙️")
                
                action_text = {
                    "approve": "Approved",
                    "review": "Review requested",
                    "reject": "Rejected"
                }.get(action_type, "Processed")
                
                update_message = f"{action_emoji} *{action_text}* by {user_name}\n\nTask `{task_id}` created"
                
                if source == "github" and routing.get("repo") and routing.get("pr_number"):
                    update_message += f"\n`@agent {action_type}` posted to PR #{routing['pr_number']}"
                elif source == "jira" and routing.get("ticket_key"):
                    update_message += f"\n`@agent {action_type}` posted to ticket `{routing['ticket_key']}`"
                
                await update_slack_message(channel, message_ts, update_message)
                logger.info("slack_button_action_processed", action=action_type, task_id=task_id, source=source, user=user_name)
            
            return {"ok": True}

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_interactivity_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
