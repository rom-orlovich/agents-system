"""Execute parsed bot commands.

This module handles execution of parsed commands, dispatching to appropriate
handlers and managing responses.

Usage:
    from shared.commands.executor import CommandExecutor
    
    executor = CommandExecutor(redis_client, github_client, slack_client)
    
    result = await executor.execute(parsed_command)
    if result.success:
        print(result.message)
"""

from __future__ import annotations

import asyncio
from typing import Optional, Callable, Awaitable, Dict, Any
import logging

from ..types import ParsedCommand, CommandResult, TaskContext
from ..models import Task
from ..enums import CommandType, TaskStatus, TaskSource, Platform
from ..constants import QUEUE_CONFIG
from .parser import CommandParser

logger = logging.getLogger("command_executor")


# Type alias for command handlers
CommandHandler = Callable[[ParsedCommand], Awaitable[CommandResult]]


class CommandExecutor:
    """Execute parsed bot commands.
    
    Handles all command types by dispatching to appropriate handlers.
    Integrates with Redis queues, GitHub MCP, and Slack.
    
    Attributes:
        redis: Redis client for queue operations
        github: GitHub client for API operations
        slack: Slack client for notifications
    
    Example:
        executor = CommandExecutor(
            redis=redis_client,
            github=github_client,
            slack=slack_client,
        )
        
        result = await executor.execute(parsed_command)
        
        if result.should_reply:
            await github.post_comment(pr_number, result.message)
    """
    
    def __init__(
        self,
        redis = None,
        github = None,
        slack = None,
        claude_code_runner = None,
    ):
        """Initialize executor with clients.
        
        Args:
            redis: Redis client for queue operations
            github: GitHub client (optional)
            slack: Slack client (optional)
            claude_code_runner: Function to run Claude Code CLI (optional)
        """
        self.redis = redis
        self.github = github
        self.slack = slack
        self.claude_code_runner = claude_code_runner
        
        self.parser = CommandParser()
        
        # Map command types to handlers
        self._handlers: Dict[CommandType, CommandHandler] = {
            CommandType.APPROVE: self._handle_approve,
            CommandType.REJECT: self._handle_reject,
            CommandType.IMPROVE: self._handle_improve,
            CommandType.STATUS: self._handle_status,
            CommandType.HELP: self._handle_help,
            CommandType.CI_STATUS: self._handle_ci_status,
            CommandType.CI_LOGS: self._handle_ci_logs,
            CommandType.RETRY_CI: self._handle_retry_ci,
            CommandType.ASK: self._handle_ask,
            CommandType.EXPLAIN: self._handle_explain,
            CommandType.FIND: self._handle_find,
            CommandType.DISCOVER: self._handle_discover,
            CommandType.UNKNOWN: self._handle_unknown,
        }
    
    async def execute(self, command: ParsedCommand) -> CommandResult:
        """Execute a parsed command.
        
        Args:
            command: Parsed command to execute
            
        Returns:
            CommandResult with success status and message
        """
        logger.info(f"Executing command: {command.command_name} ({command.command_type})")
        
        handler = self._handlers.get(command.command_type, self._handle_unknown)
        
        try:
            result = await handler(command)
            logger.info(f"Command {command.command_name} completed: success={result.success}")
            return result
        except Exception as e:
            logger.exception(f"Command {command.command_name} failed")
            return CommandResult(
                success=False,
                message=f"❌ Command failed: {str(e)}",
            )
    
    # =========================================================================
    # Core Handlers
    # =========================================================================
    
    async def _handle_approve(self, command: ParsedCommand) -> CommandResult:
        """Handle approve command - move task to execution queue."""
        task_id = command.context.get("task_id")
        
        if not task_id:
            return CommandResult(
                success=False,
                message="❌ No task found to approve. This PR may not be linked to a task.",
            )
        
        if self.redis:
            # Get task data
            task_data = await self.redis.hgetall(f"task:{task_id}")
            
            if not task_data:
                return CommandResult(
                    success=False,
                    message=f"❌ Task `{task_id}` not found.",
                )
            
            # Update status
            await self.redis.hset(f"task:{task_id}", "status", TaskStatus.APPROVED.value)
            
            # Add to execution queue
            await self.redis.rpush(QUEUE_CONFIG.execution_queue, task_id)
            
            logger.info(f"Task {task_id} approved and queued for execution")
        
        return CommandResult(
            success=True,
            message=f"""✅ **Approved!**

Task `{task_id}` has been queued for execution.

**Next Steps:**
1. 🔄 Cloning repository
2. 🧪 Running tests locally
3. 🔧 Implementing fix
4. 📤 Pushing changes

⏱️ Estimated: 5-10 minutes

I'll update this PR when complete.""",
            reaction="rocket",
        )
    
    async def _handle_reject(self, command: ParsedCommand) -> CommandResult:
        """Handle reject command."""
        task_id = command.context.get("task_id")
        reason = command.args[0] if command.args else "No reason provided"
        
        if task_id and self.redis:
            await self.redis.hset(f"task:{task_id}", "status", TaskStatus.REJECTED.value)
            await self.redis.hset(f"task:{task_id}", "rejection_reason", reason)
        
        return CommandResult(
            success=True,
            message=f"""❌ **Rejected**

Task `{task_id or 'N/A'}` has been rejected.

**Reason:** {reason}

The plan will not be executed.""",
            reaction="-1",
        )
    
    async def _handle_improve(self, command: ParsedCommand) -> CommandResult:
        """Handle improve command - re-run planning with feedback."""
        task_id = command.context.get("task_id")
        instruction = command.args[0] if command.args else None
        
        if not instruction:
            return CommandResult(
                success=False,
                message="❌ Please provide improvement instructions.\n\nExample: `@agent improve add more error handling`",
            )
        
        if task_id and self.redis:
            # Store feedback
            await self.redis.hset(f"task:{task_id}", "improvement_request", instruction)
            await self.redis.hset(f"task:{task_id}", "status", TaskStatus.PLANNING.value)
            
            # Re-queue for planning
            await self.redis.rpush(QUEUE_CONFIG.planning_queue, task_id)
        
        return CommandResult(
            success=True,
            message=f"""🔄 **Improving Plan**

I'll update the plan based on your feedback:
> {instruction}

This may take a few minutes. I'll update this PR when done.""",
            reaction="eyes",
        )
    
    async def _handle_status(self, command: ParsedCommand) -> CommandResult:
        """Handle status command."""
        task_id = command.context.get("task_id")
        
        if not task_id:
            return CommandResult(
                success=True,
                message="ℹ️ No active task found for this PR.",
            )
        
        status_info = {
            "task_id": task_id,
            "status": "unknown",
            "repository": command.context.get("repository", "unknown"),
        }
        
        if self.redis:
            task_data = await self.redis.hgetall(f"task:{task_id}")
            if task_data:
                status_info["status"] = task_data.get("status", "unknown")
                status_info["updated_at"] = task_data.get("updated_at", "unknown")
                status_info["error"] = task_data.get("error")
        
        status_emoji = {
            "pending": "⏳",
            "discovering": "🔍",
            "planning": "📝",
            "pending_approval": "👀",
            "approved": "✅",
            "executing": "⚙️",
            "completed": "🎉",
            "failed": "❌",
            "rejected": "🚫",
        }.get(status_info["status"], "❓")
        
        message = f"""## Task Status

| Field | Value |
|-------|-------|
| Task ID | `{status_info['task_id']}` |
| Status | {status_emoji} {status_info['status']} |
| Repository | {status_info['repository']} |"""
        
        if status_info.get("error"):
            message += f"\n| Error | {status_info['error']} |"
        
        return CommandResult(
            success=True,
            message=message,
        )
    
    async def _handle_help(self, command: ParsedCommand) -> CommandResult:
        """Handle help command."""
        specific_command = command.args[0] if command.args else None
        help_text = self.parser.get_help(specific_command)
        
        return CommandResult(
            success=True,
            message=help_text,
        )
    
    # =========================================================================
    # CI/CD Handlers
    # =========================================================================
    
    async def _handle_ci_status(self, command: ParsedCommand) -> CommandResult:
        """Handle ci-status command."""
        pr_number = command.context.get("pr_number")
        repository = command.context.get("repository")
        
        if not pr_number or not repository:
            return CommandResult(
                success=False,
                message="❌ Cannot check CI status - missing PR or repository information.",
            )
        
        # This would use GitHub MCP in real implementation
        message = f"""## CI Status: PR #{pr_number}

Checking CI status...

Use this command when the Claude Code skills are loaded to get real CI status via GitHub MCP.

**Expected output:**
- Overall status (passing/failing)
- Individual check statuses
- Failure details if any"""
        
        return CommandResult(
            success=True,
            message=message,
        )
    
    async def _handle_ci_logs(self, command: ParsedCommand) -> CommandResult:
        """Handle ci-logs command."""
        return CommandResult(
            success=True,
            message="""## CI Logs

This command requires Claude Code to be running with GitHub MCP enabled.

The CI Monitor skill will:
1. Find failed workflow runs
2. Get job logs using `get_job_logs`
3. Analyze the failure
4. Suggest a fix

Try: `@agent ci-status` first to see which jobs failed.""",
        )
    
    async def _handle_retry_ci(self, command: ParsedCommand) -> CommandResult:
        """Handle retry-ci command."""
        return CommandResult(
            success=True,
            message="""🔄 **Re-running CI**

This command requires Claude Code with GitHub MCP.

The system will use `rerun_failed_jobs` to retry only failed jobs.

If you want to retry all jobs, push an empty commit:
```bash
git commit --allow-empty -m "chore: retry CI"
git push
```""",
        )
    
    # =========================================================================
    # Code Understanding Handlers
    # =========================================================================
    
    async def _handle_ask(self, command: ParsedCommand) -> CommandResult:
        """Handle ask command - answer questions about code."""
        question = command.args[0] if command.args else None
        
        if not question:
            return CommandResult(
                success=False,
                message="❓ What would you like to know?\n\nExample: `@agent ask how does authentication work?`",
            )
        
        # In real implementation, this would invoke Claude Code
        return CommandResult(
            success=True,
            message=f"""🤔 **Analyzing your question...**

> {question}

This requires Claude Code to run with repository access.

The system will:
1. Search relevant code
2. Analyze the implementation
3. Provide an answer with code references""",
        )
    
    async def _handle_explain(self, command: ParsedCommand) -> CommandResult:
        """Handle explain command."""
        target = command.args[0] if command.args else None
        
        if not target:
            return CommandResult(
                success=False,
                message="❓ What would you like explained?\n\nExample: `@agent explain src/auth.js`",
            )
        
        return CommandResult(
            success=True,
            message=f"""📖 **Explaining: `{target}`**

This requires Claude Code with repository access.

I'll analyze:
- Purpose and functionality
- Key methods/functions
- Dependencies
- Usage examples""",
        )
    
    async def _handle_find(self, command: ParsedCommand) -> CommandResult:
        """Handle find command."""
        pattern = command.args[0] if command.args else None
        
        if not pattern:
            return CommandResult(
                success=False,
                message="🔍 What are you looking for?\n\nExample: `@agent find UserService`",
            )
        
        return CommandResult(
            success=True,
            message=f"""🔍 **Searching for: `{pattern}`**

This requires Claude Code with GitHub MCP.

Will search:
- File names
- Code content
- Function/class names""",
        )
    
    async def _handle_discover(self, command: ParsedCommand) -> CommandResult:
        """Handle discover command."""
        repo = command.args[0] if command.args else None
        
        return CommandResult(
            success=True,
            message=f"""🔍 **Running Discovery**

{f'Searching in: `{repo}`' if repo else 'Searching all accessible repositories'}

This will:
1. Search for related code
2. Find affected files
3. Identify dependencies
4. Update the task with findings""",
        )
    
    async def _handle_unknown(self, command: ParsedCommand) -> CommandResult:
        """Handle unknown command."""
        return CommandResult(
            success=False,
            message=f"""❓ Unknown command: `{command.raw_text}`

Use `@agent help` to see available commands.

**Did you mean:**
- `@agent approve` - Approve the plan
- `@agent status` - Check task status
- `@agent help` - Show all commands""",
        )
