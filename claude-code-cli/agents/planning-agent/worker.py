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
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from task_queue import RedisQueue
from slack_client import SlackClient
from metrics import metrics
from logging_utils import get_logger

logger = get_logger("planning-agent")

# Path to the skills directory
SKILLS_DIR = Path(__file__).parent / "skills"


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
        logger.info("Planning Agent Worker STARTED")
        logger.info("=" * 60)
        logger.info(
            "Configuration",
            queue=self.queue_name,
            timeout=settings.PLANNING_AGENT_TIMEOUT,
            skills_dir=str(SKILLS_DIR)
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
        
        # Route to appropriate skill based on action
        if action == "enrich" or source == "jira":
            skill = "jira-enrichment"
        elif action == "plan_changes" or source == "github_comment":
            skill = "plan-changes"
        elif action == "execute":
            skill = "execution"
        else:
            skill = "jira-enrichment"
        
        logger.info(f"STEP 2: Selected skill: {skill}")
        await self.run_skill(skill, task_data)

    async def run_skill(self, skill_name: str, task_data: dict):
        """Run a skill using Claude Code CLI.
        
        The skill defines:
        - The prompt (how to accomplish the task)
        - Which MCP tools to use (GitHub, Jira, Sentry)
        - Expected outputs
        
        Args:
            skill_name: Name of the skill directory
            task_data: Task context data
        """
        task_id = task_data.get("task_id", f"task-{datetime.now().timestamp()}")
        start_time = datetime.now()
        
        logger.info(
            "STEP 3: Starting skill execution",
            task_id=task_id,
            skill=skill_name,
            source=task_data.get("source")
        )
        metrics.record_task_started("planning")
        
        try:
            # Update status
            logger.info("STEP 4: Updating task status to DISCOVERING")
            await self.queue.update_task_status(task_id, TaskStatus.DISCOVERING)
            
            # Load the skill prompt
            logger.info(f"STEP 5: Loading skill prompt from {SKILLS_DIR / skill_name}")
            skill_prompt = self._load_skill(skill_name)
            if not skill_prompt:
                raise ValueError(f"Skill not found: {skill_name}")
            logger.info(
                "Skill loaded",
                skill=skill_name,
                prompt_length=len(skill_prompt)
            )
            
            # Build context from task data
            logger.info("STEP 6: Building task context")
            context = self._build_context(task_data)
            logger.info(f"Context built:\n{context}")
            
            # Full prompt = skill instructions + task context
            full_prompt = f"{skill_prompt}\n\n---\n\n## Current Task Context\n\n{context}"
            logger.info(
                "STEP 7: Full prompt prepared",
                total_length=len(full_prompt)
            )
            
            # Run Claude Code CLI
            logger.info("STEP 8: Invoking Claude Code CLI")
            result = await self._run_claude_code(full_prompt, task_id)
            
            if result["success"]:
                logger.info("STEP 9: Claude Code CLI completed successfully")
                logger.info(f"Output preview: {result['output'][:500]}...")
                
                # Extract PR URL from Claude's output
                pr_url = self._extract_pr_url(result["output"])
                logger.info(f"STEP 10: Extracted PR URL: {pr_url or 'None found'}")
                
                # Update status to pending approval
                logger.info("STEP 11: Updating task status to PENDING_APPROVAL")
                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.PENDING_APPROVAL,
                    plan=result["output"][:5000],
                    plan_url=pr_url or ""
                )
                
                # Notify Slack
                logger.info("STEP 12: Sending Slack notification")
                await self._notify_slack(task_id, task_data, result, pr_url)
                
                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_task_completed("planning", "success", duration)
                
                logger.info(
                    "SKILL COMPLETED SUCCESSFULLY",
                    task_id=task_id,
                    skill=skill_name,
                    pr_url=pr_url,
                    duration=f"{duration:.2f}s"
                )
            else:
                logger.error(
                    "Claude Code CLI failed",
                    error=result.get("error"),
                    output=result.get("output", "")[:500]
                )
                raise Exception(result.get("error", "Claude Code CLI failed"))
                
        except Exception as e:
            logger.error(
                "SKILL FAILED",
                task_id=task_id,
                skill=skill_name,
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

    def _load_skill(self, skill_name: str) -> Optional[str]:
        """Load a skill's prompt file.
        
        Args:
            skill_name: Name of the skill directory
            
        Returns:
            Skill prompt content or None if not found
        """
        skill_dir = SKILLS_DIR / skill_name
        logger.debug(f"Looking for skill in: {skill_dir}")
        
        # Try prompt.md first, then SKILL.md
        for filename in ["prompt.md", "SKILL.md"]:
            prompt_file = skill_dir / filename
            if prompt_file.exists():
                logger.debug(f"Found skill file: {prompt_file}")
                return prompt_file.read_text()
        
        logger.warning(f"No skill file found in {skill_dir}")
        return None

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
            context_lines.append(f"\n**Full Description:**\n```\n{task_data['full_description'][:2000]}\n```")
        if task_data.get("pr_url"):
            context_lines.append(f"**PR URL:** {task_data['pr_url']}")
        if task_data.get("comment"):
            context_lines.append(f"**Comment:** {task_data['comment']}")
        
        return "\n".join(context_lines) if context_lines else "No additional context provided."

    async def _run_claude_code(self, prompt: str, task_id: str) -> dict:
        """Run Claude Code CLI with the given prompt.
        
        Claude Code will:
        - Load MCP config from the target repository's .claude/ directory
        - Use MCP tools (GitHub, Jira, Sentry) as instructed by the skill
        - Create PRs, update tickets, etc. directly
        
        Args:
            prompt: The full prompt (skill + context)
            task_id: Task ID for logging
            
        Returns:
            Dict with success status and output
        """
        try:
            # Setup workspace for this task
            workspace_dir = Path("/workspace") / task_id.replace(":", "_")
            workspace_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Workspace directory: {workspace_dir}")
            
            # Save prompt to file for --append-system-prompt-file
            prompt_file = workspace_dir / "prompt.md"
            prompt_file.write_text(prompt)
            logger.info(f"Prompt saved to: {prompt_file}")
            
            # Build Claude Code CLI command
            cmd = [
                "claude",
                "-p",  # Print mode (headless)
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--allowedTools", "Read,Edit,Bash,mcp__github,mcp__sentry,mcp__atlassian",
                "--append-system-prompt-file", str(prompt_file),
                # The actual task instruction
                "Execute the task described in the system prompt. "
                "Use the MCP tools to interact with GitHub, Jira, and Sentry. "
                "Report the PR URL when complete."
            ]
            
            logger.info(
                "Executing Claude Code CLI",
                task_id=task_id,
                cwd=str(workspace_dir),
                command=" ".join(cmd[:8]) + "..."  # First 8 args
            )
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace_dir)
            )
            
            logger.info(f"Claude Code CLI process started, PID: {process.pid}")

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.PLANNING_AGENT_TIMEOUT
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
                    stderr=error[:500],
                    stdout=output[:500]
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
                logger.info("Parsed JSON output successfully")
            except json.JSONDecodeError:
                logger.debug("Output is not JSON, using raw text")
            
            return {
                "success": True,
                "output": output
            }
            
        except asyncio.TimeoutError:
            logger.error(
                "Claude Code CLI TIMEOUT",
                task_id=task_id,
                timeout=settings.PLANNING_AGENT_TIMEOUT
            )
            return {
                "success": False,
                "error": f"Timeout after {settings.PLANNING_AGENT_TIMEOUT}s",
                "output": ""
            }
        except Exception as e:
            logger.error(
                "Claude Code CLI EXCEPTION",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__
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

    async def _notify_slack(
        self,
        task_id: str,
        task_data: dict,
        result: dict,
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
                output_preview=result["output"][:200]
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
