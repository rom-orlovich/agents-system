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

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import settings
from shared.models import TaskStatus
from shared.task_queue import RedisQueue
from shared.slack_client import SlackClient
from shared.metrics import metrics
from shared.logging_utils import get_logger
from shared.token_manager import TokenManager
from shared.git_utils import GitUtils
from shared.types import GitRepository
from shared.enums import TokenStatus
from shared.constants import TIMEOUT_CONFIG
from shared.claude_runner import run_claude_streaming, extract_pr_url

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
                
                # Wait for task from queue
                task_data = await self.queue.pop(self.queue_name, timeout=0)

                if task_data:
                    logger.info("=" * 60)
                    logger.info("NEW TASK RECEIVED")
                    logger.info("=" * 60)
                    logger.info(
                        "Task details",
                        task_id=task_data.get("task_id"),
                        action=task_data.get("action"),
                        source=task_data.get("source"),
                        issue_key=task_data.get("issue_key"),
                        repository=task_data.get("repository"),
                        sentry_issue_id=task_data.get("sentry_issue_id")
                    )
                    await self.process_task(task_data)
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

    async def process_task(self, task_data: dict):
        """Process a single task - routes to appropriate skill.

        Args:
            task_data: Task data from queue
        """
        action = task_data.get("action", "default")
        source = task_data.get("source", "unknown")
        
        logger.info(
            "STEP 1: Routing task to skill",
            action=action,
            source=source
        )
        
        # Route to task type (Claude reads instructions from .claude/CLAUDE.md)
        if action == "enrich" or source == "jira":
            task_type = "jira_enrichment"
        elif action == "plan_changes" or source == "github_comment":
            task_type = "plan_changes"
        elif action == "execute":
            task_type = "execution"
        else:
            task_type = "jira_enrichment"
        
        logger.info(f"STEP 2: Task type: {task_type}")
        await self.run_task(task_type, task_data)

    async def run_task(self, task_type: str, task_data: dict):
        """Run a task using Claude Code CLI with auto-detected skills.
        
        Claude Code automatically loads instructions from .claude/CLAUDE.md
        when running from this agent's directory. We only pass the task context.
        
        Args:
            task_type: Type of task (jira_enrichment, plan_changes, execution)
            task_data: Task context data
        """
        task_id = task_data.get("task_id", f"task-{datetime.now().timestamp()}")
        start_time = datetime.now()
        
        logger.info(
            "STEP 3: Starting task execution",
            task_id=task_id,
            task_type=task_type,
            source=task_data.get("source")
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
            repository = task_data.get("repository")
            if repository:
                logger.info(f"STEP 6: Cloning/updating repository: {repository}")
                repo = GitRepository.from_full_name(repository)
                clone_result = await self.git.clone_repository(repo)
                if clone_result.success:
                    logger.info(f"Repository ready at: {self.git.get_repo_path(repo)}")
                else:
                    logger.warning("Failed to clone repository", error=clone_result.error)
            else:
                logger.info("STEP 6: No repository specified, skipping clone")
            
            # Build context from task data (Claude reads skills from .claude/CLAUDE.md)
            logger.info("STEP 7: Building task context")
            context = self._build_context(task_data)
            
            # Create task prompt - Claude auto-loads .claude/CLAUDE.md for skill instructions
            task_prompt = f"""## Task Type: {task_type}

{context}

Execute the {task_type} workflow as described in your instructions.
Report the PR URL when complete."""
            
            # Run Claude Code CLI with streaming output
            logger.info("STEP 8: Invoking Claude Code CLI with streaming (skills auto-detected)")
            result = await run_claude_streaming(
                prompt=task_prompt,
                working_dir=AGENT_DIR,
                timeout=settings.PLANNING_AGENT_TIMEOUT,
                allowed_tools="Read,Edit,Bash,mcp__github,mcp__sentry,mcp__atlassian",
                logger=logger,
                stream_json=True
            )
            
            if result.success:
                logger.info("STEP 9: Claude Code CLI completed successfully")
                logger.info(f"Duration: {result.duration_seconds:.2f}s")
                
                # PR URL already extracted by claude_runner
                pr_url = result.pr_url
                logger.info(f"STEP 10: PR URL: {pr_url or 'None found'}")
                
                # Update status to pending approval
                logger.info("STEP 11: Updating task status to PENDING_APPROVAL")
                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.PENDING_APPROVAL,
                    plan=result.output[:5000],
                    plan_url=pr_url or ""
                )
                
                # Notify Slack
                logger.info("STEP 12: Sending Slack notification")
                await self._notify_slack(task_id, task_data, result, pr_url)
                
                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_task_completed("planning", "success", duration)
                
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
            await self.slack.send_task_failed(task_id, str(e))
            
            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("planning", "failed", duration)

    def _build_context(self, task_data: dict) -> str:
        """Build context string from task data.
        
        Args:
            task_data: Task data from queue
            
        Returns:
            Formatted context string
        """
        context_lines = []
        
        # Add all relevant task fields
        if task_data.get("issue_key"):
            context_lines.append(f"**Jira Issue:** {task_data['issue_key']}")
        if task_data.get("sentry_issue_id"):
            context_lines.append(f"**Sentry Issue ID:** {task_data['sentry_issue_id']}")
        if task_data.get("repository"):
            context_lines.append(f"**Repository:** {task_data['repository']}")
        if task_data.get("description"):
            context_lines.append(f"**Description:** {task_data['description']}")
        if task_data.get("full_description"):
            context_lines.append(f"\n**Full Description:**\n```\n{task_data['full_description'][:10000]}\n```")
        if task_data.get("pr_url"):
            context_lines.append(f"**PR URL:** {task_data['pr_url']}")
        if task_data.get("comment"):
            context_lines.append(f"**Comment:** {task_data['comment']}")
        
        return "\n".join(context_lines) if context_lines else "No additional context provided."

    async def _notify_slack(
        self,
        task_id: str,
        task_data: dict,
        result,  # ClaudeResult from claude_runner
        pr_url: Optional[str]
    ):
        """Send Slack notification about task completion.
        
        Args:
            task_id: Task identifier
            task_data: Original task data
            result: Claude Code result
            pr_url: PR URL if created
        """
        repository = task_data.get("repository", "unknown/repo")
        issue_key = task_data.get("issue_key", "")
        
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
                pr_url=pr_url
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
