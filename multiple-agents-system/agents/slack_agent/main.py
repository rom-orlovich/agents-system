"""
Slack Integration Agent Implementation
======================================
Handles Slack commands and sends notifications.
"""

import json
import os
from datetime import datetime
import boto3
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.aws_lambda.async_handler import AsyncSlackRequestHandler

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings


class SlackAgent:
    """Agent for Slack interactions."""
    
    def __init__(self):
        """Initialize the Slack agent."""
        self.app = AsyncApp(
            token=settings.slack.bot_token,
            signing_secret=settings.slack.signing_secret
        )
        self.dynamodb = boto3.resource("dynamodb")
        self.tasks_table = self.dynamodb.Table(settings.dynamodb.tasks_table)
        self.step_functions = boto3.client("stepfunctions")
        
        self._register_commands()
    
    def _register_commands(self):
        """Register Slack slash commands."""
        
        @self.app.command("/agent")
        async def handle_agent_command(ack, command, respond):
            await ack()
            
            parts = command['text'].split()
            if len(parts) == 0:
                await respond(self._help_message())
                return
            
            cmd = parts[0]
            args = parts[1:]
            
            handlers = {
                "status": self._handle_status,
                "approve": self._handle_approve,
                "reject": self._handle_reject,
                "retry": self._handle_retry,
                "list": self._handle_list,
                "help": lambda r, a: r(self._help_message())
            }
            
            handler = handlers.get(cmd)
            if handler:
                await handler(respond, args, command)
            else:
                await respond(f"Unknown command: {cmd}. Use `/agent help` for usage.")
    
    def _help_message(self) -> str:
        """Generate help message."""
        return """📋 *AI Agent Commands*

`/agent status <task-id>` - Get task status
`/agent approve <task-id>` - Approve plan for execution
`/agent reject <task-id>` - Reject plan
`/agent retry <task-id>` - Retry failed task
`/agent list [status]` - List tasks (pending, running, completed)
`/agent help` - Show this message

*Examples:*
• `/agent status jira-PROJ-123-1705500000`
• `/agent approve jira-PROJ-123-1705500000`
• `/agent list pending`"""
    
    async def _handle_status(self, respond, args, command):
        """Get task status."""
        if len(args) == 0:
            await respond("Usage: `/agent status <task-id>`")
            return
        
        task_id = args[0]
        
        response = self.tasks_table.get_item(
            Key={"pk": f"TASK#{task_id}", "sk": "METADATA"}
        )
        
        if 'Item' not in response:
            await respond(f"❌ Task not found: `{task_id}`")
            return
        
        task = response['Item']
        
        status_emoji = {
            "started": "🔍",
            "discovery": "🔍",
            "planning": "📋",
            "awaiting_approval": "⏳",
            "approved": "✅",
            "executing": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(task.get('status', 'unknown'), "❓")
        
        await respond(blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Task: {task_id}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:* {status_emoji} {task.get('status', 'Unknown')}"},
                    {"type": "mrkdwn", "text": f"*Ticket:* {task.get('ticket_id', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Agent:* {task.get('current_agent', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Progress:* {task.get('progress', 0)}%"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Last Update:*\n{task.get('last_update', 'N/A')}"}
            }
        ])
    
    async def _handle_approve(self, respond, args, command):
        """Approve a plan."""
        if len(args) == 0:
            await respond("Usage: `/agent approve <task-id>`")
            return
        
        task_id = args[0]
        
        self.tasks_table.update_item(
            Key={"pk": f"TASK#{task_id}", "sk": "METADATA"},
            UpdateExpression="SET #status = :status, approved_by = :user, approved_at = :time",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "approved",
                ":user": command['user_id'],
                ":time": datetime.utcnow().isoformat()
            }
        )
        
        await respond(f"✅ Plan approved for task `{task_id}`. Execution will begin shortly.")
    
    async def _handle_reject(self, respond, args, command):
        """Reject a plan."""
        if len(args) == 0:
            await respond("Usage: `/agent reject <task-id>`")
            return
        
        task_id = args[0]
        
        self.tasks_table.update_item(
            Key={"pk": f"TASK#{task_id}", "sk": "METADATA"},
            UpdateExpression="SET #status = :status, rejected_by = :user, rejected_at = :time",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "rejected",
                ":user": command['user_id'],
                ":time": datetime.utcnow().isoformat()
            }
        )
        
        await respond(f"❌ Plan rejected for task `{task_id}`.")
    
    async def _handle_retry(self, respond, args, command):
        """Retry a failed task."""
        if len(args) == 0:
            await respond("Usage: `/agent retry <task-id>`")
            return
        
        task_id = args[0]
        
        self.tasks_table.update_item(
            Key={"pk": f"TASK#{task_id}", "sk": "METADATA"},
            UpdateExpression="SET #status = :status, retry_requested_by = :user, retry_at = :time",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "retrying",
                ":user": command['user_id'],
                ":time": datetime.utcnow().isoformat()
            }
        )
        
        await respond(f"🔄 Retry requested for task `{task_id}`.")
    
    async def _handle_list(self, respond, args, command):
        """List tasks."""
        status_filter = args[0] if args else None
        
        scan_kwargs = {}
        if status_filter:
            scan_kwargs["FilterExpression"] = "#status = :status"
            scan_kwargs["ExpressionAttributeNames"] = {"#status": "status"}
            scan_kwargs["ExpressionAttributeValues"] = {":status": status_filter}
        
        response = self.tasks_table.scan(**scan_kwargs)
        items = response.get('Items', [])[:10]
        
        if not items:
            await respond("No tasks found.")
            return
        
        task_list = []
        for item in items:
            task_id = item.get('task_id', 'Unknown')
            status = item.get('status', 'unknown')
            ticket = item.get('ticket_id', 'N/A')
            task_list.append(f"• `{task_id}` - {ticket} ({status})")
        
        await respond(f"📋 *Tasks* ({len(items)})\n\n" + "\n".join(task_list))
    
    async def send_notification(self, channel: str, notification: dict):
        """Send notification to Slack."""
        await self.app.client.chat_postMessage(
            channel=channel,
            **notification
        )


slack_agent = SlackAgent()
handler = AsyncSlackRequestHandler(slack_agent.app)


async def lambda_handler(event, context):
    """Lambda handler for Slack agent."""
    return await handler.handle(event, context)
