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
from shared.models import TaskStatus
from shared.task_queue import RedisQueue
from shared.slack_client import SlackClient
from shared.metrics import metrics
from shared.logging_utils import get_logger
from shared.token_manager import TokenManager
from shared.git_utils import GitUtils
from shared.types import GitRepository, ClaudeCodeResult
from shared.enums import TokenStatus
from shared.constants import TIMEOUT_CONFIG
from shared.claude_runner import run_claude_streaming, extract_pr_url

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
                
                # Wait for approved task from queue
                task_data = await self.queue.pop(self.queue_name, timeout=0)

                if task_data:
                    logger.info("=" * 60)
                    logger.info("NEW EXECUTION TASK RECEIVED")
                    logger.info("=" * 60)
                    logger.info(
                        "Task details",
                        task_id=task_data.get("task_id"),
                        repository=task_data.get("repository"),
                        issue_key=task_data.get("issue_key"),
                        approved_at=datetime.now().isoformat()
                    )
                    await self.process_task(task_data)
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

    async def process_task(self, task_data: dict):
        """Process execution task.

        Args:
            task_data: Task data from queue
        """
        task_id = task_data.get("task_id")
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

            # Get repository from task data
            repository = self._get_repository(task_data)
            if not repository:
                raise ValueError("No repository specified in task data")
            
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
            context = self._build_context(task_data, initial_test_result)
            
            # Create task prompt - Claude auto-loads .claude/CLAUDE.md for TDD workflow
            task_prompt = f"""## Execution Task

{context}

**Repository Path:** {repo_path}

Execute the TDD workflow as described in your instructions.
Report the PR URL when complete."""
            
            # Run Claude Code CLI with streaming output
            logger.info("STEP 8: Invoking Claude Code CLI with streaming (TDD from .claude/)")
            timeout = getattr(settings, 'EXECUTION_AGENT_TIMEOUT', 600)
            result = await run_claude_streaming(
                prompt=task_prompt,
                working_dir=AGENT_DIR,
                timeout=timeout,
                allowed_tools="Read,Edit,Write,Bash,mcp__github",
                logger=logger
            )
            
            if result.success:
                logger.info("STEP 9: Claude Code CLI completed successfully")
                logger.info(f"Duration: {result.duration_seconds:.2f}s")
                
                # PR URL already extracted by claude_runner
                pr_url = result.pr_url
                execution_time = f"{result.duration_seconds:.1f}s"
                
                # Update status to completed
                logger.info("STEP 10: Updating task status to COMPLETED")
                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    completed_at=datetime.utcnow().isoformat(),
                    pr_url=pr_url or ""
                )

                # Send completion notification
                await self.slack.send_task_completed(
                    task_id,
                    repository,
                    pr_url or task_data.get("plan_url", ""),
                    execution_time
                )

                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_task_completed("executor", "success", duration)

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
            await self.slack.send_task_failed(task_id, str(e))

            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("executor", "failed", duration)
    
    def _get_repository(self, task_data: dict) -> Optional[str]:
        """Extract repository from task data.
        
        Args:
            task_data: Task data from queue
            
        Returns:
            Repository in owner/repo format or None
        """
        # Try direct repository field
        if task_data.get("repository"):
            return task_data["repository"]
        
        # Try discovery data
        discovery_raw = task_data.get("discovery", "{}")
        try:
            discovery = json.loads(discovery_raw) if isinstance(discovery_raw, str) else discovery_raw
            if discovery.get("repository"):
                return discovery["repository"]
        except json.JSONDecodeError:
            pass
        
        # Try plan_url (extract from PR URL)
        plan_url = task_data.get("plan_url", "")
        if "github.com" in plan_url:
            # https://github.com/owner/repo/pull/123
            match = re.search(r"github\.com/([^/]+/[^/]+)", plan_url)
            if match:
                return match.group(1)
        
        return None
    
    def _build_context(self, task_data: dict, test_result) -> str:
        """Build context string from task data.
        
        Args:
            task_data: Task data from queue
            test_result: Initial test run results
            
        Returns:
            Formatted context string
        """
        lines = []
        
        # Repository info
        if task_data.get("repository"):
            lines.append(f"**Repository:** {task_data['repository']}")
        
        # Issue/ticket info
        if task_data.get("issue_key"):
            lines.append(f"**Jira Issue:** {task_data['issue_key']}")
        
        # Plan info
        if task_data.get("plan"):
            lines.append(f"\n**Approved Plan:**\n```\n{task_data['plan'][:3000]}\n```")
        
        if task_data.get("plan_url"):
            lines.append(f"**Plan PR:** {task_data['plan_url']}")
        
        # Test status
        lines.append(f"\n**Initial Test Status:**")
        lines.append(f"- Framework: {test_result.framework.value}")
        lines.append(f"- Passed: {test_result.passed}")
        lines.append(f"- Tests: {test_result.total_tests} total, {test_result.passed_tests} passed, {test_result.failed_tests} failed")
        
        if test_result.failures:
            lines.append(f"- Failures preview: {test_result.output[:500]}")
        
        # Instructions
        lines.append("\n**Instructions:**")
        lines.append("1. Create a feature branch from main")
        lines.append("2. Implement the changes as described in the plan")
        lines.append("3. Run tests locally - they MUST pass")
        lines.append("4. Commit using conventional commit format")
        lines.append("5. Push and create a PR")
        lines.append("6. Report the PR URL when complete")
        
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
