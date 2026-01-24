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
import json
from typing import Optional, Callable, Awaitable, Dict, Any
import logging

from ..models import ParsedCommand, CommandResult, GitHubTask
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
        pr_number = command.context.get("pr_number")
        repository = command.context.get("repository")

        if not self.redis:
            return CommandResult(success=False, message="❌ Redis not configured")

        try:
            # 1. Try to find existing task
            found_task = None
            if task_id:
                found_task = await self.redis.get_task(task_id)
            
            if not found_task and pr_number and repository:
                task_id = await self.redis.get_task_id_by_pr(pr_number, repository)
                if task_id:
                    found_task = await self.redis.get_task(task_id)

            # 2. If task found, update and re-queue
            if found_task:
                await self.redis.update_task_status(task_id, TaskStatus.APPROVED)
                # Re-push to execution queue
                # Ensure it's a GitHubTask or convert if needed
                if isinstance(found_task, dict):
                    # Add current PR info if missing
                    found_task.setdefault("pr_number", pr_number)
                    found_task.setdefault("repository", repository)
                    found_task["action"] = "approved"
                    exec_task = GitHubTask.model_validate(found_task)
                else:
                    exec_task = found_task
                    exec_task.action = "approved"
                
                await self.redis.push_task(QUEUE_CONFIG.execution_queue, exec_task)
                
                return CommandResult(
                    success=True,
                    message=f"✅ **Approved!**\n\nTask `{task_id}` has been queued for execution.",
                    reaction="rocket",
                    should_reply=False,
                )

            # 3. Fallback: Create new task from PR description (passed in context)
            pr_title = command.context.get("pr_title")
            pr_body = command.context.get("pr_body")
            pr_url = command.context.get("pr_url")
            
            if pr_number and repository and (pr_title or pr_body):
                comment = f"Instruction: {pr_title}\n\nContext from PR description:\n{pr_body}"
                logger.debug(f"Creating new GitHubTask with instructions: {comment[:200]}...")
                new_task = GitHubTask(
                    repository=repository,
                    pr_number=pr_number,
                    pr_url=pr_url,
                    action="approved",
                    comment=comment
                )
                new_task_id = await self.redis.push_task(QUEUE_CONFIG.execution_queue, new_task)
                
                return CommandResult(
                    success=True,
                    message=f"✅ **Approved!**\n\nI couldn't find a previous task record, so I've created a new one (`{new_task_id}`) using the PR description as the instructions for Claude.",
                    reaction="rocket",
                    should_reply=False,
                )

        except Exception as e:
            logger.exception(f"Failed to approve task")
            return CommandResult(
                success=False,
                message=f"❌ Failed to approve task: {str(e)}",
            )

        return CommandResult(
            success=False,
            message="❌ No task found to approve. Please ensure the PR has a description with instructions.",
        )
    
    async def _handle_reject(self, command: ParsedCommand) -> CommandResult:
        """Handle reject command."""
        task_id = command.context.get("task_id")
        reason = command.args[0] if command.args else "No reason provided"
        
        if task_id and self.redis:
            await self.redis.update_task_status(
                task_id, 
                TaskStatus.REJECTED, 
                rejection_reason=reason
            )
        
        return CommandResult(
            success=True,
            message=f"❌ **Rejected**\n\nTask `{task_id or 'N/A'}` has been rejected.",
            reaction="-1",
            should_reply=False,
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
        
        if not self.redis:
            return CommandResult(success=False, message="❌ Redis not configured")

        # 1. Try to find existing task
        task_data = None
        if task_id:
            task_data = await self.redis.get_task(task_id)
        
        if task_data:
            # Update status and feedback in Redis hash
            # We append the improvement request to the comment so the executor sees it in the context
            original_comment = task_data.get("comment", "")
            new_comment = f"{original_comment}\n\n**Improvement Request:** {instruction}"
            
            updates = {
                "status": TaskStatus.APPROVED,  # Set to APPROVED so it's ready for execution
                "improvement_request": instruction,
                "action": "improve",
                "comment": new_comment
            }
            
            # Add PR context if we're improving from a PR
            pr_url = command.context.get("pr_url")
            pr_number = command.context.get("pr_number")
            if pr_url:
                updates["pr_url"] = pr_url
            if pr_number:
                updates["pr_number"] = pr_number

            await self.redis.update_task_status(task_id, **updates)
            
            # Re-queue: Pydantic handles enum serialization automatically
            try:
                # Update dict for re-parsing
                task_data.update(updates)
                task_data["status"] = TaskStatus.APPROVED.value  # Ensure value for JSON
                task_data["action"] = "improve"
                task_data["improvement_request"] = instruction
                
                # Use current RedisQueue's parsing helper
                task_obj = self.redis._parse_task(json.dumps(task_data))
                
                # Push to EXECUTION queue instead of planning queue
                await self.redis.push_task(QUEUE_CONFIG.execution_queue, task_obj)
                
                return CommandResult(
                    success=True,
                    message=f"🔄 **Improving Implementation**\n\nI've queued the improvement task `{task_id}` for execution.",
                    reaction="rocket",
                    should_reply=False,
                )
            except Exception as e:
                logger.error(f"Failed to re-queue task: {e}")
                return CommandResult(success=False, message=f"❌ Failed to re-queue task: {e}")
        
        # 2. Fallback: Create new task from PR info
        pr_number = command.context.get("pr_number")
        repository = command.context.get("repository")
        pr_url = command.context.get("pr_url")
        
        if pr_number and repository:
            logger.info(f"Task {task_id or 'N/A'} not found, creating new task for improvement")
            
            # For new improvement tasks, we treat the instruction as the main comment
            comment = f"Improvement requested: {instruction}"
            
            new_task = GitHubTask(
                repository=repository,
                pr_number=pr_number,
                pr_url=pr_url,
                action="improve",
                comment=comment,
                improvement_request=instruction,
                status=TaskStatus.APPROVED
            )
            
            # Push to EXECUTION queue
            new_task_id = await self.redis.push_task(QUEUE_CONFIG.execution_queue, new_task)
            
            # Also register it so subsequent commands find it
            await self.redis.register_pr_task(
                pr_url=pr_url or f"https://github.com/{repository}/pull/{pr_number}",
                task_id=new_task_id,
                repository=repository,
                pr_number=pr_number
            )
            
            return CommandResult(
                success=True,
                message=f"🔄 **Improving**\n\nI couldn't find a previous task record, so I've created a new one (`{new_task_id}`) to handle your improvement request directly in the execution queue.",
                reaction="rocket",
                should_reply=False,
            )

        return CommandResult(
            success=False, 
            message=f"❌ Could not find task `{task_id or 'N/A'}` and missing PR context to create a new one."
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
            task_data = await self.redis.get_task_info(task_id)
            if task_data:
                status_info["status"] = task_data.get("status", "unknown")
                status_info["updated_at"] = task_data.get("updated_at", "unknown")
                status_info["error"] = task_data.get("error")
                status_info["cost_usd"] = task_data.get("cost_usd", 0)
        
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
| Repository | {status_info['repository']} |
| Cost | ${float(status_info.get('cost_usd', 0)):.4f} |"""
        
        if status_info.get("error"):
            message += f"\n| Error | {status_info['error']} |"
        
        return CommandResult(
            success=True,
            message=message,
            should_reply=False,
            reaction="bar_chart",
        )
    
    async def _handle_help(self, command: ParsedCommand) -> CommandResult:
        """Handle help command."""
        specific_command = command.args[0] if command.args else None
        help_text = self.parser.get_help(specific_command)
        
        return CommandResult(
            success=True,
            message=help_text,
            should_reply=False,
            reaction="question",
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
            should_reply=False,
            reaction="mag",
        )
    
    async def _handle_ci_logs(self, command: ParsedCommand) -> CommandResult:
        """Handle ci-logs command."""
        return CommandResult(
            success=True,
            message=message,
            should_reply=False,
            reaction="scroll",
        )
    
    async def _handle_retry_ci(self, command: ParsedCommand) -> CommandResult:
        """Handle retry-ci command."""
        return CommandResult(
            success=True,
            message=message,
            should_reply=False,
            reaction="arrows_counterclockwise",
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
            message=f"🤔 **Analyzing your question...**\n\n> {question}",
            reaction="eyes",
            should_reply=False,
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
            message=f"📖 **Explaining: `{target}`**",
            reaction="eyes",
            should_reply=False,
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
            message=f"🔍 **Searching for: `{pattern}`**",
            reaction="mag",
            should_reply=False,
        )
    
    async def _handle_discover(self, command: ParsedCommand) -> CommandResult:
        """Handle discover command."""
        repo = command.args[0] if command.args and command.args[0] else command.context.get("repository")
        pr_number = command.context.get("pr_number")
        
        if self.redis and repo:
            try:
                # Create a discovery task
                discover_task = GitHubTask(
                    repository=repo,
                    pr_number=pr_number,
                    action="discover",
                    comment=f"Discovery requested on {repo}" + (f" for PR #{pr_number}" if pr_number else "")
                )
                task_id = await self.redis.push_task(QUEUE_CONFIG.planning_queue, discover_task)
                
                return CommandResult(
                    success=True,
                    message=f"🔍 **Discovery Started!**\n\nTask `{task_id}` has been queued for code discovery.",
                    reaction="eyes",
                    should_reply=False,
                )
            except Exception as e:
                logger.exception("Failed to trigger discovery")
                return CommandResult(success=False, message=f"❌ Redis error: {str(e)}")
        
        return CommandResult(
            success=False,
            message="❌ Could not trigger discovery - missing repository information.",
            reaction="confused"
        )
    
    async def _handle_unknown(self, command: ParsedCommand) -> CommandResult:
        """Handle unknown command."""
        return CommandResult(
            success=False,
            message=f"❓ Unknown command: `{command.raw_text}`",
            reaction="confused",
            should_reply=False,
        )
