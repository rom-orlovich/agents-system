"""
Planning Agent Entry Point
==========================
CLI interface for running the planning agent.
"""

import json
import sys
from pathlib import Path

import click
import structlog

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utils import setup_logging
from planning_agent.worker import PlanningAgent

logger = structlog.get_logger(__name__)


@click.command()
@click.argument("ticket_id")
@click.option("--summary", "-s", default="", help="Ticket summary")
@click.option("--description", "-d", default="", help="Ticket description")
def main(ticket_id: str, summary: str, description: str):
    """Run the planning agent on a specific ticket."""
    setup_logging()

    task_data = {
        "source": "cli",
        "ticket_id": ticket_id,
        "summary": summary or f"Task {ticket_id}",
        "description": description,
        "priority": "Medium",
    }

    agent = PlanningAgent()
    result = agent.process_task(task_data)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
