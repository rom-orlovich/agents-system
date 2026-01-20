"""Slack webhook routes.

Handles Slack webhooks including:
- URL verification
- Button clicks (approvals/rejections)
- Slash commands (future)
- App mentions with bot commands (@agent help, etc.)
"""

import json
import re
import sys
from pathlib import Path
from fastapi import APIRouter, Request
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.config import settings
from shared.models import TaskStatus
from shared.task_queue import RedisQueue
from shared.slack_client import SlackClient
from shared.commands import CommandParser
from shared.commands.executor import CommandExecutor
from shared.enums import Platform
from shared.constants import BOT_CONFIG

router = APIRouter()
queue = RedisQueue()
slack_client = SlackClient()
command_parser = CommandParser()
command_executor = CommandExecutor(redis=queue, slack=slack_client)

logger = logging.getLogger("slack-webhook")


@router.post("/")
async def slack_webhook(request: Request):
    """Handle Slack webhook events.
    
    Processes:
    - url_verification: Slack challenge response
    - event_callback: App mentions, messages
    - block_actions: Button clicks (approve/reject)
    """
    payload = await request.json()
    
    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        logger.info("Slack URL verification")
        return {"challenge": payload.get("challenge")}
    
    # Handle interactive components (buttons)
    if "actions" in payload:
        return await handle_button_action(payload)
    
    # Handle event callbacks (messages, mentions)
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type", "")
        
        if event_type == "app_mention":
            return await handle_app_mention(event)
        
        if event_type == "message":
            return await handle_message(event)
    
    return {"status": "processed"}


async def handle_button_action(payload: dict):
    """Handle Slack button clicks (approve/reject buttons).
    
    Args:
        payload: Slack interactive payload
        
    Returns:
        Response dict
    """
    action = payload.get("actions", [{}])[0]
    action_id = action.get("action_id", "")
    task_id = action.get("value", "")
    user = payload.get("user", {}).get("username", "unknown")
    
    logger.info(f"Slack button action: {action_id} from @{user}")
    
    if action_id == "approve_task":
        task_data = await queue.get_task(task_id)
        if task_data:
            try:
                await queue.update_task_status(task_id, TaskStatus.APPROVED)

                # Re-push to execution queue using typed task
                # Parse the stored data back to a Pydantic model
                raw_data = task_data.get("data", task_data)
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)

                # Use the queue's _parse_task to get the correct typed task
                json_str = json.dumps(raw_data)
                typed_task = queue._parse_task(json_str)

                # Update status on the task model before re-pushing
                typed_task.status = TaskStatus.APPROVED

                # Re-push using typed method
                await queue.push_task(settings.EXECUTION_QUEUE, typed_task)

                logger.info(f"Task {task_id} approved via Slack by @{user}")

                return {
                    "response_type": "in_channel",
                    "text": f"✅ Task `{task_id}` approved by @{user} and queued for execution!"
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse task data for {task_id}: {e}")
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to process task `{task_id}`: Invalid task data"
                }
            except ValueError as e:
                logger.error(f"Failed to validate task {task_id}: {e}")
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to process task `{task_id}`: {str(e)}"
                }
            except Exception as e:
                logger.exception(f"Unexpected error processing task {task_id}")
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to approve task `{task_id}`: {str(e)}"
                }
        else:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Task `{task_id}` not found"
            }
    
    elif action_id == "reject_task":
        await queue.update_task_status(task_id, TaskStatus.REJECTED)
        
        logger.info(f"Task {task_id} rejected via Slack by @{user}")
        
        return {
            "response_type": "in_channel",
            "text": f"❌ Task `{task_id}` rejected by @{user}"
        }
    
    return {"status": "processed"}


async def handle_app_mention(event: dict):
    """Handle app mention events (@bot commands).
    
    Args:
        event: Slack event object
        
    Returns:
        Response dict
    """
    text = event.get("text", "")
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts", event.get("ts"))
    ts = event.get("ts")  # Original message timestamp
    user = event.get("user", "")
    
    logger.info(f"App mention from <@{user}>: {text[:100]}...")
    
    # Build context for command parser
    context = {
        "channel": channel,
        "thread_ts": thread_ts,
        "ts": ts,  # For reactions
        "user": user,
    }
    
    # Parse the command (prepend @agent since the bot was mentioned)
    # The actual bot mention will be like <@U12345> so we need to normalize
    # Replace Slack user mention with @agent
    normalized_text = re.sub(r"<@[A-Z0-9]+>", "@agent", text)
    
    parsed = command_parser.parse(
        text=normalized_text,
        platform=Platform.SLACK,
        context=context
    )
    
    if not parsed:
        logger.warning(f"Could not parse command from: {text[:50]}")
        return {
            "response_type": "ephemeral",
            "text": f"I didn't understand that. Try `@{BOT_CONFIG.name} help` for commands."
        }
    
    logger.info(f"Parsed command: {parsed.command_name}")
    
    # Execute the command
    result = await command_executor.execute(parsed)
    
    logger.info(
        f"Command executed: {parsed.command_name}",
        extra={"success": result.success, "should_reply": result.should_reply}
    )
    
    # Add reaction to acknowledge we received the command
    if ts:
        reaction = result.reaction or ("eyes" if result.success else "confused")
        await slack_client.add_reaction(
            channel=channel,
            timestamp=ts,
            reaction=reaction
        )
        logger.info(f"Added {reaction} reaction to command in Slack")
    
    # Post message if specifically requested
    if result.should_reply:
        await slack_client.reply_in_thread(
            channel=channel,
            thread_ts=thread_ts,
            text=result.message
        )
        logger.info(f"Posted response message to Slack")
    
    return {
        "status": "executed",
        "command": parsed.command_name,
        "success": result.success
    }


async def handle_message(event: dict):
    """Handle direct messages to the bot.
    
    Args:
        event: Slack event object
        
    Returns:
        Response dict
    """
    # Ignore bot messages to prevent loops
    if event.get("bot_id"):
        return {"status": "ignored", "reason": "bot message"}
    
    # Only handle DMs (channel starts with D)
    channel = event.get("channel", "")
    if not channel.startswith("D"):
        return {"status": "ignored", "reason": "not DM"}
    
    text = event.get("text", "")
    user = event.get("user", "")
    
    logger.info(f"DM from <@{user}>: {text[:100]}...")
    
    # For DMs, prepend @agent since they're talking to us directly
    normalized_text = f"@agent {text}"
    
    context = {
        "channel": channel,
        "user": user,
    }
    
    parsed = command_parser.parse(
        text=normalized_text,
        platform=Platform.SLACK,
        context=context
    )
    
    if parsed:
        result = await command_executor.execute(parsed)
        return {
            "status": "executed",
            "command": parsed.command_name
        }
    
    return {"status": "processed"}


@router.get("/test")
async def test_slack_webhook():
    """Test endpoint."""
    return {
        "status": "Slack webhook endpoint is working",
        "bot_name": BOT_CONFIG.name,
        "bot_tags": BOT_CONFIG.tags
    }
