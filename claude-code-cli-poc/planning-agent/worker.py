"""
Planning Agent Worker
=====================
Polls Redis queue for planning tasks and runs Claude Code CLI.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import structlog

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import get_settings
from shared.utils import setup_logging
from webhook_server.queue import get_queue

logger = structlog.get_logger(__name__)


class PlanningAgent:
    """Planning and Discovery Agent using Claude Code CLI."""

    def __init__(self):
        self.settings = get_settings()
        self.workspace = Path(self.settings.agent.workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = self.settings.agent.task_timeout_minutes * 60

    def process_task(self, task_data: dict) -> dict:
        """Process a planning task."""
        ticket_id = task_data.get("ticket_id", "unknown")
        logger.info("Processing planning task", ticket_id=ticket_id)

        # Prepare workspace
        task_dir = self.workspace / ticket_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Write task data for Claude to read
        task_file = task_dir / "task.json"
        with open(task_file, "w") as f:
            json.dump(task_data, f, indent=2)

        # Run Claude Code CLI
        try:
            result = self._run_claude(task_dir, task_data)
            return result
        except Exception as e:
            logger.exception("Planning agent failed", ticket_id=ticket_id)
            return {
                "status": "failed",
                "ticket_id": ticket_id,
                "error": str(e),
            }

    def _run_claude(self, task_dir: Path, task_data: dict) -> dict:
        """Execute Claude Code CLI in the task directory."""
        ticket_id = task_data.get("ticket_id", "unknown")
        summary = task_data.get("summary", "Fix issue")

        # Build prompt
        prompt = f"""You have a new task to analyze and plan.

## Ticket Information
- **ID:** {ticket_id}
- **Summary:** {summary}
- **Description:** {task_data.get('description', 'N/A')}
- **Priority:** {task_data.get('priority', 'Medium')}
- **Source:** {task_data.get('source', 'jira')}

Read the full task details from `task.json` in the current directory.

Follow the instructions in CLAUDE.md to:
1. Discover relevant repositories and files
2. Create a detailed implementation plan (PLAN.md)
3. Open a Draft PR for approval

When done, save your results to `result.json`.
"""

        # Run Claude CLI
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--print",
            prompt,
        ]

        logger.info("Running Claude CLI", ticket_id=ticket_id)

        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = self.settings.agent.claude_config_dir

        result = subprocess.run(
            cmd,
            cwd=str(task_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=env,
        )

        if result.returncode != 0:
            logger.error(
                "Claude CLI failed",
                ticket_id=ticket_id,
                stderr=result.stderr[:500],
            )
            raise Exception(f"Claude CLI failed: {result.stderr[:200]}")

        # Read result file if it exists
        result_file = task_dir / "result.json"
        if result_file.exists():
            with open(result_file) as f:
                return json.load(f)

        # Return basic success if no result file
        return {
            "status": "success",
            "ticket_id": ticket_id,
            "output": result.stdout[:1000],
        }


def run_worker():
    """Run the planning agent worker loop."""
    setup_logging()
    logger.info("Starting planning agent worker")

    queue = get_queue()
    agent = PlanningAgent()

    while True:
        try:
            # Wait for task from queue
            task_data = queue.dequeue_planning_task(timeout=10)

            if task_data is None:
                continue

            # Process task
            result = agent.process_task(task_data)

            # Store result
            ticket_id = task_data.get("ticket_id", "unknown")
            queue.store_result(f"planning:{ticket_id}", result)

            logger.info(
                "Planning task completed",
                ticket_id=ticket_id,
                status=result.get("status"),
            )

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.exception("Worker error", error=str(e))


if __name__ == "__main__":
    run_worker()
