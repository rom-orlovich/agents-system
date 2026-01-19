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

logger = get_logger("executor-agent")

# Path to the skills directory
SKILLS_DIR = Path(__file__).parent / "skills"


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
        
        # Log available skills on startup
        available_skills = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
        logger.info(
            "Worker initialized",
            queue=self.queue_name,
            skills_dir=str(SKILLS_DIR),
            available_skills=available_skills
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
            skills_dir=str(SKILLS_DIR)
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
            
            # Load the skill prompt
            logger.info("STEP 7: Loading execution skill")
            skill_prompt = self._load_skill("pr-workflow")
            if not skill_prompt:
                # Fallback to tdd-workflow if pr-workflow doesn't exist
                skill_prompt = self._load_skill("tdd-workflow")
            
            if not skill_prompt:
                raise ValueError("No execution skill found (pr-workflow or tdd-workflow)")
            
            # Build context from task data
            logger.info("STEP 8: Building execution context")
            context = self._build_context(task_data, initial_test_result)
            
            # Full prompt = skill instructions + task context
            full_prompt = f"{skill_prompt}\n\n---\n\n## Execution Context\n\n{context}"
            
            # Run Claude Code CLI
            logger.info("STEP 9: Invoking Claude Code CLI")
            result = await self._run_claude_code(full_prompt, task_id, repo_path)
            
            if result["success"]:
                logger.info("STEP 10: Claude Code CLI completed successfully")
                logger.info(f"Output preview: {result['output'][:500]}...")
                
                # Extract PR URL from output
                pr_url = self._extract_pr_url(result["output"])
                execution_time = f"{(datetime.now() - start_time).total_seconds():.1f}s"
                
                # Update status to completed
                logger.info("STEP 11: Updating task status to COMPLETED")
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
                raise Exception(result.get("error", "Claude Code CLI failed"))

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
    
    def _load_skill(self, skill_name: str) -> Optional[str]:
        """Load a skill's prompt file.
        
        Args:
            skill_name: Name of the skill directory
            
        Returns:
            Skill prompt content or None if not found
        """
        skill_dir = SKILLS_DIR / skill_name
        logger.debug(f"Looking for skill in: {skill_dir}")
        
        # Try SKILL.md first, then prompt.md
        for filename in ["SKILL.md", "prompt.md"]:
            prompt_file = skill_dir / filename
            if prompt_file.exists():
                logger.debug(f"Found skill file: {prompt_file}")
                return prompt_file.read_text()
        
        logger.warning(f"No skill file found in {skill_dir}")
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
    
    async def _run_claude_code(
        self,
        prompt: str,
        task_id: str,
        repo_path: Path
    ) -> dict:
        """Run Claude Code CLI with the given prompt.
        
        Args:
            prompt: The full prompt (skill + context)
            task_id: Task ID for logging
            repo_path: Path to the cloned repository
            
        Returns:
            Dict with success status and output
        """
        try:
            # Save prompt to file
            prompt_file = repo_path / ".claude-prompt.md"
            prompt_file.write_text(prompt)
            logger.info(f"Prompt saved to: {prompt_file}")
            
            # Build Claude Code CLI command
            cmd = [
                "claude",
                "-p",  # Print mode (headless)
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Read,Edit,Write,Bash,mcp__github",
                "--append-system-prompt-file", str(prompt_file),
                # The actual task instruction
                "Execute the implementation plan. "
                "Run tests locally before pushing. "
                "Create a PR and report the URL."
            ]
            
            logger.info(
                "Executing Claude Code CLI",
                task_id=task_id,
                cwd=str(repo_path),
                command=" ".join(cmd[:8]) + "..."
            )
            
            timeout = getattr(settings, 'EXECUTION_AGENT_TIMEOUT', 600)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path)
            )
            
            logger.info(f"Claude Code CLI process started, PID: {process.pid}")

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            output = stdout.decode("utf-8")
            error = stderr.decode("utf-8")
            
            logger.info(
                "Claude Code CLI process completed",
                return_code=process.returncode,
                stdout_length=len(output),
                stderr_length=len(error)
            )
            
            if error:
                logger.warning(f"Claude Code CLI stderr: {error[:1000]}")
            
            if process.returncode != 0:
                logger.error(
                    "Claude Code CLI exited with error",
                    task_id=task_id,
                    return_code=process.returncode,
                    stderr=error[:500]
                )
                return {
                    "success": False,
                    "error": error or f"Exit code: {process.returncode}",
                    "output": output
                }
            
            # Try to parse JSON output
            try:
                result_data = json.loads(output)
                output = result_data.get("result", output)
            except json.JSONDecodeError:
                pass
            
            return {
                "success": True,
                "output": output
            }
            
        except asyncio.TimeoutError:
            timeout = getattr(settings, 'EXECUTION_AGENT_TIMEOUT', 600)
            logger.error(
                "Claude Code CLI TIMEOUT",
                task_id=task_id,
                timeout=timeout
            )
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
                "output": ""
            }
        except Exception as e:
            logger.error(
                "Claude Code CLI EXCEPTION",
                task_id=task_id,
                error=str(e)
            )
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def _extract_pr_url(self, output: str) -> Optional[str]:
        """Extract GitHub PR URL from Claude's output.
        
        Args:
            output: Claude Code output
            
        Returns:
            PR URL if found
        """
        pattern = r"https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/pull/\d+"
        match = re.search(pattern, output)
        if match:
            logger.info(f"Found PR URL in output: {match.group(0)}")
            return match.group(0)
        
        logger.warning("No PR URL found in Claude output")
        return None


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("INITIALIZING EXECUTOR AGENT WORKER")
    logger.info("=" * 60)
    
    worker = ExecutorAgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
