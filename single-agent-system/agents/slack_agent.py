"""
Slack Integration Agent Implementation
======================================
Handles Slack commands and sends notifications.
Mirrors the distributed system's slack_agent/main.py
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import structlog

from config import settings

logger = structlog.get_logger(__name__)


class SlackAgent:
    """Agent for Slack interactions."""
    
    def __init__(self, mcp_gateway):
        """Initialize the Slack agent."""
        self.slack = mcp_gateway.get_tool("slack")
        self.task_store = mcp_gateway.get_task_store()
        
        self._load_prompts()
        logger.info("slack_agent_initialized")
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "slack"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = ""
    
    def handle_command(self, command: str, args: List[str], user_id: str = "local") -> str:
        """Handle a slash command.
        
        Args:
            command: Command name (status, approve, reject, list, help)
            args: Command arguments
            user_id: User who issued the command
            
        Returns:
            Response message
        """
        handlers = {
            "status": self._handle_status,
            "approve": self._handle_approve,
            "reject": self._handle_reject,
            "retry": self._handle_retry,
            "list": self._handle_list,
            "help": self._handle_help
        }
        
        handler = handlers.get(command)
        if handler:
            return handler(args, user_id)
        else:
            return f"Unknown command: {command}. Use 'help' for usage."
    
    def _handle_help(self, args: List[str], user_id: str) -> str:
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
    
    def _handle_status(self, args: List[str], user_id: str) -> str:
        """Get task status."""
        if not args:
            return "Usage: `/agent status <task-id>`"
        
        task_id = args[0]
        item = self.task_store.get_item(f"TASK#{task_id}", "METADATA")
        
        if not item:
            return f"❌ Task not found: `{task_id}`"
        
        status_emoji = {
            "started": "🔍",
            "discovery": "🔍",
            "planning": "📋",
            "awaiting_approval": "⏳",
            "approved": "✅",
            "executing": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(item.get("status", "unknown"), "❓")
        
        return f"""📋 *Task: {task_id}*

*Status:* {status_emoji} {item.get('status', 'Unknown')}
*Ticket:* {item.get('ticket_id', 'N/A')}
*Progress:* {item.get('progress', 0)}%

*Last Update:* {item.get('last_update', 'N/A')}"""
    
    def _handle_approve(self, args: List[str], user_id: str) -> str:
        """Approve a plan."""
        if not args:
            return "Usage: `/agent approve <task-id>`"
        
        task_id = args[0]
        
        self.task_store.update_item(
            f"TASK#{task_id}",
            "METADATA",
            {
                "status": "approved",
                "approved_by": user_id,
                "approved_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info("plan_approved", task_id=task_id, user=user_id)
        return f"✅ Plan approved for task `{task_id}`. Execution will begin shortly."
    
    def _handle_reject(self, args: List[str], user_id: str) -> str:
        """Reject a plan."""
        if not args:
            return "Usage: `/agent reject <task-id>`"
        
        task_id = args[0]
        
        self.task_store.update_item(
            f"TASK#{task_id}",
            "METADATA",
            {
                "status": "rejected",
                "rejected_by": user_id,
                "rejected_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info("plan_rejected", task_id=task_id, user=user_id)
        return f"❌ Plan rejected for task `{task_id}`."
    
    def _handle_retry(self, args: List[str], user_id: str) -> str:
        """Retry a failed task."""
        if not args:
            return "Usage: `/agent retry <task-id>`"
        
        task_id = args[0]
        
        self.task_store.update_item(
            f"TASK#{task_id}",
            "METADATA",
            {
                "status": "retrying",
                "retry_requested_by": user_id,
                "retry_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info("retry_requested", task_id=task_id, user=user_id)
        return f"🔄 Retry requested for task `{task_id}`."
    
    def _handle_list(self, args: List[str], user_id: str) -> str:
        """List tasks."""
        status_filter = args[0] if args else None
        
        items = self.task_store.scan(filter_status=status_filter)
        
        if not items:
            return "No tasks found."
        
        task_list = []
        for item in items[:10]:
            task_id = item.get("task_id", "Unknown")
            status = item.get("status", "unknown")
            ticket = item.get("ticket_id", "N/A")
            task_list.append(f"• `{task_id}` - {ticket} ({status})")
        
        return f"📋 *Tasks* ({len(items)})\n\n" + "\n".join(task_list)
    
    def send_notification(self, notification_type: str, data: Dict[str, Any]):
        """Send a notification to Slack.
        
        Args:
            notification_type: Type of notification
            data: Notification data
        """
        if notification_type == "plan_ready":
            self.slack.send_approval_request(
                title=data.get("title", "Plan Ready for Review"),
                description=data.get("description", ""),
                ticket_id=data.get("ticket_id", ""),
                pr_url=data.get("pr_url")
            )
        
        elif notification_type == "task_complete":
            self.slack.send_agent_update(
                agent_name="AI Agent",
                status="success",
                message=f"Task complete: {data.get('summary', '')}",
                ticket_id=data.get("ticket_id"),
                pr_url=data.get("pr_url")
            )
        
        elif notification_type == "escalation":
            self.slack.send_error_notification(
                title="Human Intervention Required",
                error_message=data.get("error", ""),
                details=data
            )
    
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run Slack agent command.
        
        Args:
            request: Contains command, args, user_id
            
        Returns:
            Response dict
        """
        command = request.get("command", "help")
        args = request.get("args", [])
        user_id = request.get("user_id", "local")
        
        response = self.handle_command(command, args, user_id)
        
        return {"response": response}
