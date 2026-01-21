"""
Planning Agent plugin.

Orchestrates planning tasks by invoking Claude Code CLI with appropriate skills.
"""

import asyncio
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from core.agent_base import (
    BaseAgent,
    AgentMetadata,
    AgentCapability,
    AgentContext,
    AgentResult,
    AgentUsageMetrics,
)

# Import shared modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from task_queue import RedisQueue
from slack_client import SlackClient

logger = logging.getLogger(__name__)

# Path to the skills directory
SKILLS_DIR = Path(__file__).parent.parent / "planning-agent" / "skills"


class PlanningAgent(BaseAgent):
    """
    Planning Agent - creates implementation plans for bug fixes and features.

    Uses Claude Code CLI with skill-based prompts and MCP tools to:
    - Analyze Sentry errors
    - Enrich Jira tickets
    - Create implementation plans
    - Generate PRs with plan details
    """

    def __init__(self):
        self.queue = RedisQueue()
        self.slack = SlackClient()

        # Log available skills on init
        if SKILLS_DIR.exists():
            available_skills = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
            logger.info(f"Planning Agent initialized with skills: {available_skills}")
        else:
            logger.warning(f"Skills directory not found: {SKILLS_DIR}")

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="planning-agent",
            display_name="Planning Agent",
            description="Creates implementation plans for bug fixes and features using Claude Code CLI",
            capabilities=[
                AgentCapability.PLANNING,
                AgentCapability.ANALYSIS,
                AgentCapability.ENRICHMENT
            ],
            version="2.0.0",
            enabled=True,
            max_retries=2,
            timeout_seconds=settings.PLANNING_AGENT_TIMEOUT
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute planning agent logic.

        Workflow:
        1. Determine appropriate skill based on task action
        2. Load skill prompt
        3. Build task context
        4. Run Claude Code CLI with skill + context
        5. Extract PR URL from output
        6. Update task status and notify Slack

        Args:
            context: AgentContext with task data

        Returns:
            AgentResult with plan output and PR URL
        """
        task = context.task
        task_id = context.task_id
        session_id = context.session_id

        logger.info(
            f"Planning Agent executing for task {task_id} "
            f"(session: {session_id})"
        )

        # Update task status to DISCOVERING
        await self.queue.update_task_status(task_id, TaskStatus.DISCOVERING)

        # Determine skill based on task action
        skill_name = self._select_skill(task)
        logger.info(f"Selected skill: {skill_name}")

        # Load skill prompt
        skill_prompt = self._load_skill(skill_name)
        if not skill_prompt:
            raise ValueError(f"Skill not found: {skill_name}")

        logger.info(f"Loaded skill prompt ({len(skill_prompt)} chars)")

        # Build context from task
        task_context = self._build_context(task)
        logger.info(f"Built task context:\n{task_context}")

        # Full prompt = skill instructions + task context
        full_prompt = f"{skill_prompt}\n\n---\n\n## Current Task Context\n\n{task_context}"

        # Run Claude Code CLI
        logger.info("Invoking Claude Code CLI...")
        start_time = datetime.now()

        result = await self._run_claude_code(full_prompt, task_id, session_id)

        duration = (datetime.now() - start_time).total_seconds()

        if not result["success"]:
            raise Exception(result.get("error", "Claude Code CLI failed"))

        # Extract PR URL from output
        pr_url = self._extract_pr_url(result["output"])
        logger.info(f"Extracted PR URL: {pr_url or 'None found'}")

        # Update task status to PENDING_APPROVAL
        await self.queue.update_task_status(
            task_id,
            TaskStatus.PENDING_APPROVAL,
            plan=result["output"][:5000],
            plan_url=pr_url or ""
        )

        # Notify Slack
        await self._notify_slack(task_id, task, result, pr_url)

        # Return result
        return AgentResult(
            success=True,
            agent_name=self.metadata.name,
            session_id=session_id,
            output={
                "plan": result["output"][:5000],
                "pr_url": pr_url,
                "skill_used": skill_name,
            },
            usage=AgentUsageMetrics(
                # TODO: Extract actual token usage from Claude Code CLI
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                total_cost_usd=0.0,
                model_used="claude-sonnet-4.5"
            ),
            next_agent="executor-agent"  # Chain to executor after approval
        )

    def _select_skill(self, task: Dict[str, Any]) -> str:
        """
        Select appropriate skill based on task action/source.

        Args:
            task: Task data

        Returns:
            Skill name (directory name in skills/)
        """
        action = task.get("action", "default")
        source = task.get("source", "unknown")

        # Route to appropriate skill
        if action == "enrich" or source == "jira":
            return "jira-enrichment"
        elif action == "plan_changes" or source == "github_comment":
            return "plan-changes"
        elif action == "execute":
            return "execution"
        else:
            # Default to jira-enrichment
            return "jira-enrichment"

    def _load_skill(self, skill_name: str) -> Optional[str]:
        """
        Load a skill's prompt file.

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

    def _build_context(self, task: Dict[str, Any]) -> str:
        """
        Build context string from task data.

        Args:
            task: Task data

        Returns:
            Formatted context string for Claude
        """
        context_lines = []

        # Add all relevant task fields
        if task.get("issue_key"):
            context_lines.append(f"**Jira Issue:** {task['issue_key']}")
        if task.get("sentry_issue_id"):
            context_lines.append(f"**Sentry Issue ID:** {task['sentry_issue_id']}")
        if task.get("repository"):
            context_lines.append(f"**Repository:** {task['repository']}")
        if task.get("description"):
            context_lines.append(f"**Description:** {task['description']}")
        if task.get("full_description"):
            context_lines.append(
                f"\n**Full Description:**\n```\n{task['full_description'][:2000]}\n```"
            )
        if task.get("pr_url"):
            context_lines.append(f"**PR URL:** {task['pr_url']}")
        if task.get("comment"):
            context_lines.append(f"**Comment:** {task['comment']}")

        return "\n".join(context_lines) if context_lines else "No additional context provided."

    async def _run_claude_code(
        self,
        prompt: str,
        task_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Run Claude Code CLI with the given prompt.

        Claude Code will:
        - Load MCP config from the target repository's .claude/ directory
        - Use MCP tools (GitHub, Jira, Sentry) as instructed by the skill
        - Create PRs, update tickets, etc. directly

        Args:
            prompt: The full prompt (skill + context)
            task_id: Task ID for logging
            session_id: Session ID for tracking

        Returns:
            Dict with success status, output, and error (if any)
        """
        try:
            # Setup workspace for this task
            workspace_dir = Path("/workspace") / session_id.replace(":", "_")
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
                f"Executing Claude Code CLI (session: {session_id})\n"
                f"Working directory: {workspace_dir}"
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
                timeout=self.metadata.timeout_seconds
            )

            output = stdout.decode("utf-8")
            error = stderr.decode("utf-8")

            logger.info(
                f"Claude Code CLI completed (return code: {process.returncode}, "
                f"output: {len(output)} chars, stderr: {len(error)} chars)"
            )

            if error:
                logger.warning(f"Claude Code CLI stderr: {error[:1000]}")

            if process.returncode != 0:
                logger.error(
                    f"Claude Code CLI exited with error (code: {process.returncode})"
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
                "output": output,
                "error": None
            }

        except asyncio.TimeoutError:
            logger.error(
                f"Claude Code CLI TIMEOUT after {self.metadata.timeout_seconds}s"
            )
            return {
                "success": False,
                "error": f"Timeout after {self.metadata.timeout_seconds}s",
                "output": ""
            }
        except Exception as e:
            logger.exception(f"Claude Code CLI EXCEPTION: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }

    @staticmethod
    def _extract_pr_url(output: str) -> Optional[str]:
        """
        Extract GitHub PR URL from Claude's output.

        Args:
            output: Claude Code output

        Returns:
            PR URL if found, None otherwise
        """
        pattern = r"https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/pull/\d+"
        match = re.search(pattern, output)
        if match:
            url = match.group(0)
            logger.info(f"Found PR URL in output: {url}")
            return url

        logger.warning("No PR URL found in Claude output")
        return None

    async def _notify_slack(
        self,
        task_id: str,
        task: Dict[str, Any],
        result: Dict[str, Any],
        pr_url: Optional[str]
    ):
        """
        Send Slack notification about task completion.

        Args:
            task_id: Task identifier
            task: Task data
            result: Claude Code result
            pr_url: PR URL if created
        """
        repository = task.get("repository", "unknown/repo")
        issue_key = task.get("issue_key", "")

        if pr_url:
            logger.info(f"Sending Slack approval request for {task_id}")
            await self.slack.send_plan_approval_request(
                task_id=task_id,
                repository=repository,
                risk_level="medium",
                estimated_minutes=15,
                pr_url=pr_url
            )
            logger.info("Slack notification sent successfully")
        else:
            logger.warning(f"No PR URL - sending failure notification for {task_id}")
            await self.slack.send_task_failed(
                task_id,
                "Analysis complete but no PR was created. Check the logs."
            )
