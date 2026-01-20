"""Executor Agent queue worker.

Executes approved tasks by:
1. Cloning the repository
2. Running tests locally (TDD workflow - tests first!)
3. Invoking Claude Code CLI with pr-workflow skill
4. Pushing changes and creating a PR

All actual code work is done by Claude Code via the pr-workflow skill.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import re

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import settings
from shared.models import (
    GitRepository,
    AnyTask,
    JiraTask,
    GitHubTask,
)
from shared.task_queue import RedisQueue
from shared.enums import TaskStatus, TaskSource
from shared.slack_client import SlackClient
from shared.metrics import metrics
from shared.logging_utils import get_logger
from shared.token_manager import TokenManager
from shared.git_utils import GitUtils
from shared.claude_runner import run_claude_streaming, extract_pr_url
from shared.github_client import GitHubClient
from shared.database import save_task_to_db

logger = get_logger("executor-agent")

# Agent directory (contains .claude/CLAUDE.md for auto-detection)
AGENT_DIR = Path(__file__).parent


class ExecutorAgentWorker:
    """Executor Agent queue worker.
    
    Executes approved plans by invoking Claude Code CLI with execution skills.
    Handles the full TDD workflow: clone → test → implement → test → commit → push → PR.
    """

    def __init__(self):
        """Initialize worker."""
        self.queue = RedisQueue()
        self.slack = SlackClient()
        self.queue_name = settings.EXECUTION_QUEUE
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
        logger.info("Executor Agent Worker STARTED")
        logger.info("=" * 60)
        logger.info(
            "Configuration",
            queue=self.queue_name,
            timeout=settings.EXECUTION_AGENT_TIMEOUT if hasattr(settings, 'EXECUTION_AGENT_TIMEOUT') else 600,
            agent_dir=str(AGENT_DIR)
        )

        poll_count = 0
        while True:
            try:
                poll_count += 1
                
                # Log every 10th poll to show we're alive
                if poll_count % 10 == 0:
                    logger.debug(f"Polling queue... (poll #{poll_count})")
                
                # Wait for approved task from queue (typed)
                task = await self.queue.pop_task(self.queue_name, timeout=0)

                if task:
                    logger.info("=" * 60)
                    logger.info("NEW EXECUTION TASK RECEIVED")
                    logger.info("=" * 60)
                    logger.info(
                        "Task details",
                        task_id=task.task_id,
                        repository=getattr(task, "repository", None),
                        source=task.source.value,
                        approved_at=datetime.now().isoformat()
                    )
                    await self.process_task(task)
                    logger.info("=" * 60)
                    logger.info("TASK EXECUTION COMPLETE")
                    logger.info("=" * 60)

            except Exception as e:
                logger.error(
                    "Error in worker loop",
                    error=str(e),
                    error_type=type(e).__name__
                )
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                metrics.record_error("executor", "worker_loop")
                await asyncio.sleep(5)

    async def process_task(self, task: AnyTask):
        """Process execution task.

        Args:
            task: Typed task from queue
        """
        task_id = task.task_id
        start_time = datetime.now()

        logger.info("STEP 1: Starting execution", task_id=task_id)
        metrics.record_task_started("executor")

        try:
            # Check token status first
            logger.info("STEP 2: Checking OAuth token status")
            token_result = await self.token_manager.ensure_valid()
            if not token_result.success:
                logger.warning(
                    "Token not valid",
                    status=token_result.status.value,
                    error=token_result.error
                )
            else:
                logger.info(f"Token valid for {token_result.credentials.minutes_until_expiry:.1f} min")
            
            # Update status to executing
            logger.info("STEP 3: Updating task status to EXECUTING")
            await self.queue.update_task_status(task_id, TaskStatus.EXECUTING)

            # Get repository from task
            repository = self._get_repository(task)
            if not repository:
                raise ValueError("No repository specified in task")
            
            logger.info(f"STEP 4: Repository: {repository}")
            
            # Send Slack notification
            await self.slack.send_execution_started(task_id, repository)

            # Clone or update repository
            logger.info(f"STEP 5: Cloning/updating repository")
            repo = GitRepository.from_full_name(repository)
            clone_result = await self.git.clone_repository(repo)

            if not clone_result.success:
                raise Exception(f"Failed to clone repository: {clone_result.error}")

            repo_path = self.git.get_repo_path(repo)
            logger.info(f"Repository ready at: {repo_path}")

            # Read project's CLAUDE.md if it exists (NEW!)
            logger.info("STEP 5.5: Checking for project CLAUDE.md")
            project_rules = None
            project_claude_md = Path(repo_path) / "CLAUDE.md"
            if project_claude_md.exists():
                try:
                    with open(project_claude_md, 'r') as f:
                        project_rules = f.read()
                    logger.info(f"Found project CLAUDE.md ({len(project_rules)} chars)")
                except Exception as e:
                    logger.warning(f"Failed to read project CLAUDE.md: {e}")
            else:
                logger.info("No project CLAUDE.md found")
            
            # Run initial tests (TDD - tests should fail or pass first)
            logger.info("STEP 6: Running initial tests (TDD baseline)")
            initial_test_result = await self.git.run_tests(repo_path)
            logger.info(
                "Initial test results",
                passed=initial_test_result.passed,
                total=initial_test_result.total_tests,
                framework=initial_test_result.framework.value
            )
            
            # Build execution context (Claude reads TDD workflow from .claude/CLAUDE.md)
            logger.info("STEP 7: Building execution context")
            context = self._build_context(task, initial_test_result, project_rules)
            
            # Create task prompt - Claude auto-loads .claude/CLAUDE.md for TDD workflow
            task_prompt = f"""## Execution Task

{context}

**IMPORTANT:** Before starting, change your current directory to the repository path below:
**Repository Path:** `{repo_path}`

Execute the TDD workflow as described in your instructions using the provided Implementation Plan.
All code changes must be made in the repository at the path above.
Report the PR URL when complete."""
            
            logger.info("STEP 7.5: Task prompt built", prompt_preview=task_prompt[:500] + "...")
            
            # Run Claude Code CLI with streaming output
            logger.info("STEP 8: Invoking Claude Code CLI with streaming (TDD from .claude/)")
            logger.info(f"Using model: {settings.CLAUDE_CODING_MODEL} (Sonnet for coding/execution)")
            timeout = getattr(settings, 'EXECUTION_AGENT_TIMEOUT', 600)
            result = await run_claude_streaming(
                prompt=task_prompt,
                working_dir=AGENT_DIR,
                timeout=timeout,
                allowed_tools="Read,Edit,Write,Bash,mcp__github",
                logger=logger,
                stream_json=True,
                model=settings.CLAUDE_CODING_MODEL,
                env={
                    "CLAUDE_TASK_ID": task_id,
                    "CLAUDE_ACCOUNT_ID": self.token_manager.get_account_id()
                }
            )
            
            if result.success:
                logger.info("STEP 9: Claude Code CLI completed successfully")
                logger.info(f"Duration: {result.duration_seconds:.2f}s")
                
                # PR URL already extracted by claude_runner
                pr_url = result.pr_url or getattr(task, "pr_url", None)
                execution_time = f"{result.duration_seconds:.1f}s"
                
                # Post final comment to GitHub if PR exists
                if pr_url:
                    try:
                        github = GitHubClient()
                        cost_info = f"**Cost:** ${result.total_cost_usd:.4f}" if result.total_cost_usd is not None else ""
                        usage_info = f"**Tokens:** In: {result.input_tokens}, Out: {result.output_tokens}, Cache: {result.cache_read_tokens}"
                        summary = f"### ✅ Execution Complete\n\nI have implemented the changes as described in the plan.\n\n**Duration:** {execution_time}\n{cost_info}\n{usage_info}\n**Status:** All tests passed\n"
                        if result.pr_url:
                            summary += f"**PR:** {result.pr_url}"
                        
                        await github.post_comment_from_url(pr_url, summary)
                        logger.info(f"Summary comment posted to {pr_url}")
                    except Exception as ge:
                        logger.error(f"Failed to post summary comment: {ge}")

                # Update status to completed
                logger.info("STEP 10: Updating task status to COMPLETED")
                jira_link = f"{settings.JIRA_URL.rstrip('/')}/browse/{task.issue_key}" if isinstance(task, JiraTask) and settings.JIRA_URL else None
                
                # Update task object for persistence
                if jira_link:
                    task.jira_url = jira_link

                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    completed_at=datetime.utcnow().isoformat(),
                    pr_url=pr_url or "",
                    cost_usd=result.total_cost_usd,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    cache_read_tokens=result.cache_read_tokens,
                    cache_creation_tokens=result.cache_creation_tokens,
                    duration_seconds=result.duration_seconds,
                    repository_url=f"https://github.com/{repository}" if repository else None,
                    jira_url=jira_link
                )
                
                # Save to Persistent DB
                try:
                    # Get updated task data suitable for DB
                    db_task_data = {
                        "task_id": task_id,
                        "source": task.source.value if hasattr(task.source, "value") else str(task.source),
                        "status": TaskStatus.COMPLETED.value,
                        "queued_at": task.queued_at,
                        "completed_at": datetime.utcnow().isoformat(),
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
                    logger.info("STEP 10.1: Task saved to database")
                except Exception as dbe:
                    logger.error(f"Failed to save task to DB: {dbe}")

                # Register PR mapping for bot commands
                if pr_url and repository:
                    try:
                        # Extract PR number from URL
                        # https://github.com/owner/repo/pull/123
                        match = re.search(r"/pull/(\d+)", pr_url)
                        if match:
                            pr_number_val = int(match.group(1))
                            logger.info(f"STEP 10.5: Registering PR #{pr_number_val} for task {task_id}")
                            await self.queue.register_pr_task(
                                pr_url=pr_url,
                                task_id=task_id,
                                repository=repository,
                                pr_number=pr_number_val
                            )
                    except Exception as re_err:
                        logger.error(f"Failed to register PR task: {re_err}")

                # Send completion notification
                await self.slack.send_task_completed(
                    task_id,
                    repository,
                    pr_url or getattr(task, "pr_url", ""),
                    execution_time,
                    cost_usd=result.total_cost_usd
                )

                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_task_completed("executor", "success", duration)
                metrics.record_usage(
                    "executor",
                    result.total_cost_usd or 0,
                    result.input_tokens,
                    result.output_tokens,
                    result.cache_read_tokens,
                    result.cache_creation_tokens
                )

                logger.info(
                    "EXECUTION COMPLETED SUCCESSFULLY",
                    task_id=task_id,
                    pr_url=pr_url,
                    duration=f"{duration:.2f}s"
                )
            else:
                raise Exception(result.error or "Claude Code CLI failed")

        except Exception as e:
            logger.error(
                "EXECUTION FAILED",
                task_id=task_id,
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
            
            # Save failure to DB
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
            metrics.record_task_completed("executor", "failed", duration)
    
    def _get_repository(self, task: AnyTask) -> Optional[str]:
        """Extract repository from typed task.
        
        Args:
            task: Typed task from queue
            
        Returns:
            Repository in owner/repo format or None
        """
        # Try direct repository attribute
        repository = getattr(task, "repository", None)
        if repository:
            return repository
        
        # Try pr_url (extract from PR URL) for GitHub tasks
        pr_url = getattr(task, "pr_url", None) or ""
        if "github.com" in pr_url:
            # https://github.com/owner/repo/pull/123
            match = re.search(r"github\.com/([^/]+/[^/]+)", pr_url)
            if match:
                return match.group(1)
        
        return None
    
    def _build_context(self, task: AnyTask, test_result, project_rules: Optional[str] = None) -> str:
        """Build context string from typed task.

        Args:
            task: Typed task from queue
            test_result: Initial test run results
            project_rules: Optional project-specific rules from CLAUDE.md

        Returns:
            Formatted context string
        """
        lines = []

        # Add project-specific rules if available
        if project_rules:
            lines.append("## Project-Specific Rules (from repository CLAUDE.md)")
            lines.append("```")
            lines.append(project_rules)
            lines.append("```")
            lines.append("\n**IMPORTANT:** Follow these project-specific rules and conventions.")
            lines.append("")
        
        # Repository info
        repository = getattr(task, "repository", None)
        if repository:
            lines.append(f"**Repository:** {repository}")
        
        # Issue/ticket info based on task type
        if isinstance(task, JiraTask):
            lines.append(f"**Jira Issue:** {task.issue_key}")
        
        # PR info for GitHub tasks
        if isinstance(task, GitHubTask):
            if task.pr_url:
                lines.append(f"**PR URL:** {task.pr_url}")
            if task.pr_number:
                lines.append(f"**PR Number:** {task.pr_number}")
            if task.comment:
                lines.append(f"\n**Implementation Plan / Instructions:**\n{task.comment}")
        
        # Test status
        lines.append(f"\n**Initial Test Status:**")
        lines.append(f"- Framework: {test_result.framework.value}")
        lines.append(f"- Passed: {test_result.passed}")
        lines.append(f"- Tests: {test_result.total_tests} total, {test_result.passed_tests} passed, {test_result.failed_tests} failed")
        
        if test_result.failures:
            lines.append(f"- Failures preview: {test_result.output[:500]}")
        
        # Instructions
        lines.append("\n**Strict Constraints:**")
        lines.append("- **NEVER** modify build scripts (package.json, Makefile, etc.) just to pass the pipeline.")
        lines.append("- **NEVER** modify test configurations (lint-staged, husky hooks, CI workflows) to bypass failures.")
        lines.append("- **FIX THE CODE** or the actual tests instead of the infrastructure.")
        
        lines.append("\n**Workflow Instructions:**")
        
        # Check for PR info on any task type (it might be injected)
        pr_number = getattr(task, "pr_number", None)
        if not pr_number and getattr(task, "pr_url", None):
            try:
                # Try to extract from URL if number not explicit
                match = re.search(r"/pull/(\d+)", task.pr_url)
                if match:
                    pr_number = int(match.group(1))
            except:
                pass

        if pr_number:
            lines.append(f"1. Use `gh pr view {pr_number} --json headRefName` to find the PR branch.")
            lines.append(f"2. Checkout and push to that EXISTING branch. DO NOT create a new PR.")
        else:
            lines.append("1. Create a feature branch from main.")
        
        lines.append("2. Implement the changes as described in the plan.")
        lines.append("3. Run tests locally - they MUST pass.")
        lines.append("4. Commit using conventional commit format.")
        lines.append("5. Push your changes.")
        
        if not pr_number:
            lines.append("6. Create a PR if one doesn't exist.")
            
        lines.append("7. Report the PR URL when complete.")
        
        return "\n".join(lines)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("INITIALIZING EXECUTOR AGENT WORKER")
    logger.info("=" * 60)
    
    worker = ExecutorAgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
