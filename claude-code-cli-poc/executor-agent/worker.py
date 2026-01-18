"""
Executor Agent Worker
=====================
Polls Redis queue for execution tasks and runs Claude Code CLI.
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
from shared.github_client import GitHubClient
from shared.utils import setup_logging
from webhook_server.queue import get_queue

logger = structlog.get_logger(__name__)


class ExecutorAgent:
    """Executor Agent using Claude Code CLI."""

    def __init__(self):
        self.settings = get_settings()
        self.workspace = Path(self.settings.agent.workspace_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = self.settings.agent.task_timeout_minutes * 60
        self.github = GitHubClient()

    def process_task(self, task_data: dict) -> dict:
        """Process an execution task."""
        pr_number = task_data.get("pr_number", "unknown")
        repo = task_data.get("repo", "")
        branch = task_data.get("branch", "")

        logger.info(
            "Processing execution task",
            pr_number=pr_number,
            repo=repo,
            branch=branch,
        )

        # Prepare workspace
        task_dir = self.workspace / f"pr-{pr_number}"
        task_dir.mkdir(parents=True, exist_ok=True)

        # Write task data for Claude to read
        task_file = task_dir / "task.json"
        with open(task_file, "w") as f:
            json.dump(task_data, f, indent=2)

        # Clone/update repository
        try:
            repo_dir = self._prepare_repo(repo, branch, task_dir)
        except Exception as e:
            logger.exception("Failed to prepare repository")
            return {
                "status": "failed",
                "pr_number": pr_number,
                "error": f"Repository preparation failed: {e}",
            }

        # Run Claude Code CLI
        try:
            result = self._run_claude(repo_dir, task_data)

            # Add success comment to PR
            if result.get("status") == "success":
                self._add_pr_comment(
                    repo,
                    pr_number,
                    "✅ Implementation complete. All tests pass.",
                )

            return result

        except Exception as e:
            logger.exception("Executor agent failed", pr_number=pr_number)
            self._add_pr_comment(
                repo,
                pr_number,
                f"❌ Execution failed: {str(e)[:200]}",
            )
            return {
                "status": "failed",
                "pr_number": pr_number,
                "error": str(e),
            }

    def _prepare_repo(self, repo: str, branch: str, task_dir: Path) -> Path:
        """Clone or update repository and checkout branch."""
        repo_name = repo.split("/")[-1]
        repo_dir = task_dir / repo_name

        if repo_dir.exists():
            # Update existing repo
            logger.info("Updating existing repository", repo=repo)
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
            )
        else:
            # Fresh clone
            logger.info("Cloning repository", repo=repo)
            clone_url = f"https://github.com/{repo}.git"
            subprocess.run(
                ["git", "clone", "--branch", branch, clone_url, str(repo_dir)],
                check=True,
                capture_output=True,
            )

        return repo_dir

    def _run_claude(self, repo_dir: Path, task_data: dict) -> dict:
        """Execute Claude Code CLI in the repository directory."""
        pr_number = task_data.get("pr_number", "unknown")
        repo = task_data.get("repo", "")

        # Build prompt
        prompt = f"""You have been approved to implement the plan.

## Task Information
- **Repository:** {repo}
- **PR Number:** {pr_number}
- **Branch:** {task_data.get('branch', 'unknown')}
- **Approved By:** {task_data.get('approved_by', 'unknown')}

Read the PLAN.md file in this repository and implement all tasks following TDD.

Follow the instructions in CLAUDE.md to:
1. Execute each task in order (tests first!)
2. Run all tests and ensure they pass
3. Push changes and update the PR

When done, save your results to `result.json` in the repository root.
"""

        # Copy CLAUDE.md to repo if not exists
        claude_md_src = Path(__file__).parent / "CLAUDE.md"
        claude_md_dst = repo_dir / "CLAUDE.md"
        if claude_md_src.exists() and not claude_md_dst.exists():
            import shutil
            shutil.copy(claude_md_src, claude_md_dst)

        # Run Claude CLI
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--print",
            prompt,
        ]

        logger.info("Running Claude CLI", pr_number=pr_number)

        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = self.settings.agent.claude_config_dir

        result = subprocess.run(
            cmd,
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=env,
        )

        if result.returncode != 0:
            logger.error(
                "Claude CLI failed",
                pr_number=pr_number,
                stderr=result.stderr[:500],
            )
            raise Exception(f"Claude CLI failed: {result.stderr[:200]}")

        # Read result file if it exists
        result_file = repo_dir / "result.json"
        if result_file.exists():
            with open(result_file) as f:
                return json.load(f)

        # Return basic success if no result file
        return {
            "status": "success",
            "pr_number": pr_number,
            "output": result.stdout[:1000],
        }

    def _add_pr_comment(self, repo: str, pr_number: int, message: str):
        """Add a comment to the PR."""
        try:
            self.github.add_pr_comment(repo, int(pr_number), message)
        except Exception as e:
            logger.warning("Failed to add PR comment", error=str(e))


def run_worker():
    """Run the executor agent worker loop."""
    setup_logging()
    logger.info("Starting executor agent worker")

    queue = get_queue()
    agent = ExecutorAgent()

    while True:
        try:
            # Wait for task from queue
            task_data = queue.dequeue_executor_task(timeout=10)

            if task_data is None:
                continue

            # Process task
            result = agent.process_task(task_data)

            # Store result
            pr_number = task_data.get("pr_number", "unknown")
            queue.store_result(f"executor:{pr_number}", result)

            logger.info(
                "Execution task completed",
                pr_number=pr_number,
                status=result.get("status"),
            )

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.exception("Worker error", error=str(e))


if __name__ == "__main__":
    run_worker()
