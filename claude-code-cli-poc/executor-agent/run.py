"""
Executor Agent Entry Point
==========================
CLI interface for running the executor agent.
"""

import json
import sys
from pathlib import Path

import click
import structlog

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utils import setup_logging
from executor_agent.worker import ExecutorAgent

logger = structlog.get_logger(__name__)


@click.command()
@click.argument("repo")
@click.argument("pr_number", type=int)
@click.option("--branch", "-b", required=True, help="Branch name to checkout")
def main(repo: str, pr_number: int, branch: str):
    """Run the executor agent on a specific PR."""
    setup_logging()

    task_data = {
        "source": "cli",
        "repo": repo,
        "pr_number": pr_number,
        "branch": branch,
        "approved_by": "manual",
    }

    agent = ExecutorAgent()
    result = agent.process_task(task_data)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
