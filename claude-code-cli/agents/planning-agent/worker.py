"""Planning Agent queue worker.

Minimal orchestrator that invokes Claude Code CLI with skills.
All actual work (Sentry analysis, Jira updates, PR creation) is done
by Claude Code via MCP tools as defined in the skills.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import settings
from shared.models import (
    GitRepository,
    AnyTask,
    JiraTask,
    SentryTask,
    GitHubTask,
    SlackTask,
)
from shared.task_queue import RedisQueue
from shared.enums import TaskStatus, TaskSource
from shared.slack_client import SlackClient
from shared.metrics import metrics
from shared.logging_utils import get_logger
from shared.token_manager import TokenManager
from shared.git_utils import GitUtils
from shared.claude_runner import run_claude_streaming, extract_pr_url

from shared.claude_runner import run_claude_streaming, extract_pr_url
from shared.database import save_task_to_db

logger = get_logger("planning-agent")

# Agent directory (contains .claude/CLAUDE.md for auto-detection)
AGENT_DIR = Path(__file__).parent


class PlanningAgentWorker:
    """Planning Agent queue worker.
    
    This is a minimal orchestrator. All actual work is done by Claude Code
    via MCP tools (GitHub, Jira, Sentry) as defined in skills.
    """

    def __init__(self):
        """Initialize worker."""
        self.queue = RedisQueue()
        self.slack = SlackClient()
        self.queue_name = settings.PLANNING_QUEUE
        self.token_manager = TokenManager()
        self.git = GitUtils()
        
        # Verify .claude/CLAUDE.md exists for auto-detection
        claude_md = AGENT_DIR / ".claude" / "CLAUDE.md"
        logger.info(
            "Worker initialized",
            queue=self.queue_name,
            agent_dir=str(AGENT_DIR),
            claude_md_exists=claude_md.exists()
        )

    async def run(self):
        """Main worker loop."""
        logger.info("=" * 60)
        logger.info("Planning Agent Worker STARTED")
        logger.info("=" * 60)
        logger.info(
            "Configuration",
            queue=self.queue_name,
            timeout=settings.PLANNING_AGENT_TIMEOUT,
            agent_dir=str(AGENT_DIR)
        )

        poll_count = 0
        while True:
            try:
                poll_count += 1
                
                # Log every 10th poll to show we're alive
                if poll_count % 10 == 0:
                    logger.debug(f"Polling queue... (poll #{poll_count})")
                
                # Wait for task from queue (typed)
                task = await self.queue.pop_task(self.queue_name, timeout=0)

                if task:
                    logger.info("=" * 60)
                    logger.info("NEW TASK RECEIVED")
                    logger.info("=" * 60)
                    
                    # Log task details based on type
                    if isinstance(task, JiraTask):
                        logger.info(
                            "Task details (Jira)",
                            task_id=task.task_id,
                            action=task.action,
                            source=task.source.value,
                            issue_key=task.issue_key,
                            repository=task.repository,
                            sentry_issue_id=task.sentry_issue_id
                        )
                    elif isinstance(task, SentryTask):
                        logger.info(
                            "Task details (Sentry)",
                            task_id=task.task_id,
                            source=task.source.value,
                            sentry_issue_id=task.sentry_issue_id,
                            repository=task.repository
                        )
                    else:
                        logger.info(
                            "Task details",
                            task_id=task.task_id,
                            source=task.source.value
                        )
                    
                    await self.process_task(task)
                    logger.info("=" * 60)
                    logger.info("TASK PROCESSING COMPLETE")
                    logger.info("=" * 60)

            except Exception as e:
                logger.error(
                    "Error in worker loop",
                    error=str(e),
                    error_type=type(e).__name__
                )
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                metrics.record_error("planning", "worker_loop")
                await asyncio.sleep(5)

    async def process_task(self, task: AnyTask):
        """Process a single task - routes to appropriate skill.

        Args:
            task: Typed task from queue
        """
        # Determine task type based on Pydantic model type
        if isinstance(task, JiraTask):
            action = task.action
            source = TaskSource.JIRA.value
            if action == "enrich" or task.sentry_issue_id:
                task_type = "jira_enrichment"
            elif action == "approve":
                task_type = "execution"
            else:
                task_type = "jira_enrichment"
        elif isinstance(task, SentryTask):
            action = "analyze"
            source = TaskSource.SENTRY.value
            task_type = "sentry_analysis"
        elif isinstance(task, GitHubTask):
            action = task.action or "review"
            source = TaskSource.GITHUB.value
            if action == "discover":
                task_type = "discovery"
            else:
                task_type = "plan_changes"
        else:
            action = "default"
            source = task.source.value
            task_type = "jira_enrichment"
        
        logger.info(
            "STEP 1: Routing task to skill",
            action=action,
            source=source
        )
        
        logger.info(f"STEP 2: Task type: {task_type}")
        await self.run_task(task_type, task)

    async def run_task(self, task_type: str, task: AnyTask):
        """Run a task using Claude Code CLI with auto-detected skills.
        
        Claude Code automatically loads instructions from .claude/CLAUDE.md
        when running from this agent's directory. We only pass the task context.
        
        Args:
            task_type: Type of task (jira_enrichment, plan_changes, execution)
            task: Typed task from queue
        """
        task_id = task.task_id
        start_time = datetime.now()
        
        logger.info(
            "STEP 3: Starting task execution",
            task_id=task_id,
            task_type=task_type,
            source=task.source.value
        )
        metrics.record_task_started("planning")
        
        try:
            # Check token status first
            logger.info("STEP 4: Checking OAuth token status")
            token_result = await self.token_manager.ensure_valid()
            if not token_result.success:
                logger.warning(
                    "Token not valid",
                    status=token_result.status.value,
                    error=token_result.error
                )
            else:
                logger.info(f"Token valid for {token_result.credentials.minutes_until_expiry:.1f} min")
            
            # Update status
            logger.info("STEP 5: Updating task status to DISCOVERING")
            await self.queue.update_task_status(task_id, TaskStatus.DISCOVERING)
            
            # Clone or update repository if specified
            repository = getattr(task, "repository", None)
            project_rules = None
            working_dir = AGENT_DIR
            if repository:
                logger.info(f"STEP 6: Cloning/updating repository: {repository}")
                repo = GitRepository.from_full_name(repository)
                clone_result = await self.git.clone_repository(repo)
                if clone_result.success:
                    working_dir = Path(self.git.get_repo_path(repo))
                    logger.info(f"Repository ready at: {working_dir}")

                    # Read project's CLAUDE.md if it exists (NEW!)
                    logger.info("STEP 6.5: Checking for project CLAUDE.md")
                    project_claude_md = working_dir / "CLAUDE.md"
                    if project_claude_md.exists():
                        try:
                            with open(project_claude_md, 'r') as f:
                                project_rules = f.read()
                            logger.info(f"Found project CLAUDE.md ({len(project_rules)} chars)")
                        except Exception as e:
                            logger.warning(f"Failed to read project CLAUDE.md: {e}")
                    else:
                        logger.info("No project CLAUDE.md found")
                else:
                    logger.warning("Failed to clone repository", error=clone_result.error)
            else:
                logger.info("STEP 6: No repository specified, skipping clone")
            
            # Build context from task (Claude reads skills from .claude/CLAUDE.md)
            logger.info("STEP 7: Building task context")
            context = self._build_context(task)
            
            # Create task prompt - Claude auto-loads .claude/CLAUDE.md for skill instructions
            repo_instruction = ""
            if repository:
                repo_instruction = f"""**IMPORTANT:** Before starting, change your current directory to: `{working_dir}`

Use the local repository at the path above for all code operations."""

            # Include project-specific rules if found
            project_rules_section = ""
            if project_rules:
                project_rules_section = f"""

## Project-Specific Rules (from repository CLAUDE.md)

```
{project_rules}
```

**IMPORTANT:** Follow these project-specific rules and conventions when creating plans and making changes."""

            task_prompt = f"""## Task Type: {task_type}

{context}

{repo_instruction}{project_rules_section}

Execute the {task_type} workflow as described in your instructions.
Report the PR URL when complete."""
            
            logger.info("STEP 8: Task prompt built", prompt_preview=task_prompt[:500] + "...")
            
            # Run Claude Code CLI with streaming output
            logger.info("STEP 8: Invoking Claude Code CLI with streaming (skills auto-detected)")
            logger.info(f"Using model: {settings.CLAUDE_PLANNING_MODEL} (Opus for planning/discovery)")
            result = await run_claude_streaming(
                prompt=task_prompt,
                working_dir=AGENT_DIR,
                timeout=settings.PLANNING_AGENT_TIMEOUT,
                allowed_tools="Read,Edit,Bash,mcp__github,mcp__sentry,mcp__atlassian",
                logger=logger,
                stream_json=True,
                model=settings.CLAUDE_PLANNING_MODEL,
                env={
                    "CLAUDE_TASK_ID": task_id,
                    "CLAUDE_ACCOUNT_ID": self.token_manager.get_account_id()
                }
            )
            
            if result.success:
                logger.info("STEP 9: Claude Code CLI completed successfully")
                logger.info(f"Duration: {result.duration_seconds:.2f}s")
                
                # PR URL already extracted by claude_runner
                pr_url = result.pr_url
                logger.info(f"STEP 10: PR URL: {pr_url or 'None found'}")
                
                # Update status to pending approval
                logger.info("STEP 11: Updating task status to PENDING_APPROVAL")
                jira_link = f"{settings.JIRA_URL.rstrip('/')}/browse/{task.issue_key}" if isinstance(task, JiraTask) and settings.JIRA_URL else None
                
                # Update task object for persistence
                if jira_link:
                    task.jira_url = jira_link

                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.PENDING_APPROVAL,
                    plan=result.output[:5000],
                    plan_url=pr_url or "",
                    cost_usd=result.total_cost_usd,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    cache_read_tokens=result.cache_read_tokens,
                    cache_creation_tokens=result.cache_creation_tokens,
                    duration_seconds=result.duration_seconds,
                    pr_url=pr_url,
                    repository_url=f"https://github.com/{repository}" if repository else None,
                    jira_url=jira_link
                )

                # Save to Persistent DB
                try:
                    # Get updated task data suitable for DB
                    db_task_data = {
                        "task_id": task_id,
                        "source": task.source.value if hasattr(task.source, "value") else str(task.source),
                        "status": TaskStatus.PENDING_APPROVAL.value,
                        "queued_at": task.queued_at,
                        "updated_at": datetime.utcnow().isoformat(),
                         # Not technically completed, but this phase is done
                        "cost_usd": result.total_cost_usd,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "cache_read_tokens": result.cache_read_tokens,
                        "cache_creation_tokens": result.cache_creation_tokens,
                        "duration_seconds": result.duration_seconds,
                        "repository": repository,
                        "pr_url": pr_url,
                        "issue_key": getattr(task, "issue_key", None) or task.metadata.get("issue_key"),
                        "account_id": self.token_manager.get_account_id(),
                        "data": task.model_dump() if hasattr(task, "model_dump") else json.loads(task.json())
                    }
                    save_task_to_db(db_task_data)
                    logger.info("STEP 11.1: Task saved to database")
                except Exception as dbe:
                    logger.error(f"Failed to save task to DB: {dbe}")

                # Register PR mapping for bot commands
                if pr_url and repository:
                    try:
                        # Extract PR number from URL
                        # https://github.com/owner/repo/pull/123
                        match = re.search(r"/pull/(\d+)", pr_url)
                        if match:
                            pr_number = int(match.group(1))
                            logger.info(f"STEP 11.5: Registering PR #{pr_number} for task {task_id}")
                            await self.queue.register_pr_task(
                                pr_url=pr_url,
                                task_id=task_id,
                                repository=repository,
                                pr_number=pr_number
                            )
                    except Exception as re_err:
                        logger.error(f"Failed to register PR task: {re_err}")
                
                # Notify Slack
                logger.info("STEP 12: Sending Slack notification")
                await self._notify_slack(task_id, task, result, pr_url, result.total_cost_usd)
                
                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_task_completed("planning", "success", duration)
                metrics.record_usage(
                    "planning",
                    result.total_cost_usd or 0,
                    result.input_tokens,
                    result.output_tokens,
                    result.cache_read_tokens,
                    result.cache_creation_tokens
                )
                
                logger.info(
                    "TASK COMPLETED SUCCESSFULLY",
                    task_id=task_id,
                    task_type=task_type,
                    pr_url=pr_url,
                    duration=f"{duration:.2f}s"
                )
            else:
                logger.error(
                    "Claude Code CLI failed",
                    error=result.error,
                    return_code=result.return_code
                )
                raise Exception(result.error or "Claude Code CLI failed")
                
        except Exception as e:
            logger.error(
                "TASK FAILED",
                task_id=task_id,
                task_type=task_type,
                error=str(e),
                error_type=type(e).__name__
            )
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            await self.queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            try:
                save_task_to_db({
                    "task_id": task_id,
                    "source": task.source.value if hasattr(task.source, "value") else str(task.source),
                    "status": TaskStatus.FAILED.value,
                    "queued_at": task.queued_at,
                    "error": str(e),
                    "repository": getattr(task, "repository", None),
                    "account_id": self.token_manager.get_account_id(),
                    "data": task.model_dump() if hasattr(task, "model_dump") else json.loads(task.json())
                })
            except Exception as dbe:
                 logger.error(f"Failed to save failed task to DB: {dbe}")
            await self.slack.send_task_failed(task_id, str(e))
            
            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("planning", "failed", duration)

    def _build_context(self, task: AnyTask) -> str:
        """Build context string from typed task.
        
        Args:
            task: Typed task from queue
            
        Returns:
            Formatted context string
        """
        context_lines = []
        
        # Add improvement request if present
        if getattr(task, "improvement_request", None):
             context_lines.append(f"## 🔄 IMPROVEMENT REQUEST\nThe user has requested the following improvements to the previous plan/code:\n\n> {task.improvement_request}\n\nPlease address these specific points in your new plan.")
        
        # Add fields based on task type
        if isinstance(task, JiraTask):
            context_lines.append(f"**Jira Issue:** {task.issue_key}")
            if task.sentry_issue_id:
                context_lines.append(f"**Sentry Issue ID:** {task.sentry_issue_id}")
            if task.repository:
                context_lines.append(f"**Repository:** {task.repository}")
            if task.description:
                context_lines.append(f"**Description:** {task.description}")
            if task.full_description:
                context_lines.append(f"\n**Full Description:**\n```\n{task.full_description[:10000]}\n```")
        
        elif isinstance(task, SentryTask):
            context_lines.append(f"**Sentry Issue ID:** {task.sentry_issue_id}")
            context_lines.append(f"**Repository:** {task.repository}")
            if task.description:
                context_lines.append(f"**Description:** {task.description}")
        
        elif isinstance(task, GitHubTask):
            context_lines.append(f"**Repository:** {task.repository}")
            if task.pr_number:
                context_lines.append(f"**PR Number:** {task.pr_number}")
            if task.pr_url:
                context_lines.append(f"**PR URL:** {task.pr_url}")
            if task.comment:
                context_lines.append(f"\n**Task Instructions:**\n{task.comment}")
        
        elif isinstance(task, SlackTask):
            context_lines.append(f"**Channel:** {task.channel}")
            context_lines.append(f"**User:** {task.user}")
            context_lines.append(f"**Text:** {task.text}")
        
        return "\n".join(context_lines) if context_lines else "No additional context provided."

    async def _notify_slack(
        self,
        task_id: str,
        task: AnyTask,
        result,  # ClaudeResult from claude_runner
        pr_url: Optional[str],
        cost_usd: Optional[float] = None
    ):
        """Send Slack notification about task completion.
        
        Args:
            task_id: Task identifier
            task: Typed task from queue
            result: Claude Code result
            pr_url: PR URL if created
        """
        repository = getattr(task, "repository", None) or "unknown/repo"
        
        if pr_url:
            logger.info(
                "Sending Slack approval request",
                task_id=task_id,
                repository=repository,
                pr_url=pr_url
            )
            await self.slack.send_plan_approval_request(
                task_id=task_id,
                repository=repository,
                risk_level="medium",
                estimated_minutes=15,
                pr_url=pr_url,
                cost_usd=cost_usd
            )
            logger.info("Slack notification sent successfully")
        else:
            logger.warning(
                "No PR URL - sending failure notification",
                task_id=task_id,
                output_preview=result.output
            )
            await self.slack.send_task_failed(
                task_id,
                f"Analysis complete but no PR was created. Check the logs."
            )


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("INITIALIZING PLANNING AGENT WORKER")
    logger.info("=" * 60)
    
    worker = PlanningAgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
