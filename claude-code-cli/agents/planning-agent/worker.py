"""Planning Agent queue worker."""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from queue import RedisQueue
from slack_client import SlackClient
from github_client import GitHubClient
from metrics import metrics


class PlanningAgentWorker:
    """Planning Agent queue worker."""

    def __init__(self):
        """Initialize worker."""
        self.queue = RedisQueue()
        self.slack = SlackClient()
        self.github = GitHubClient()
        self.queue_name = settings.PLANNING_QUEUE

    async def run(self):
        """Main worker loop."""
        print(f"🚀 Planning Agent Worker started")
        print(f"📥 Listening on queue: {self.queue_name}")

        while True:
            try:
                # Wait for task from queue
                task_data = await self.queue.pop(self.queue_name, timeout=0)

                if task_data:
                    await self.process_task(task_data)

            except Exception as e:
                print(f"❌ Error in worker loop: {e}")
                metrics.record_error("planning", "worker_loop")
                await asyncio.sleep(5)

    async def process_task(self, task_data: dict):
        """Process a single task.

        Args:
            task_data: Task data from queue
        """
        task_id = task_data.get("task_id", f"task-{datetime.now().timestamp()}")
        start_time = datetime.now()

        print(f"📋 Processing task: {task_id}")
        metrics.record_task_started("planning")

        try:
            # Update status to discovering
            await self.queue.update_task_status(
                task_id,
                TaskStatus.DISCOVERING
            )

            # Simulate Claude Code CLI execution (placeholder)
            # In production, this would call: claude --prompt-file prompt.md
            print(f"  🔍 Running discovery for {task_id}")
            await asyncio.sleep(2)  # Simulate processing

            # Mock discovery results
            discovery = {
                "repository": task_data.get("repository", "unknown/repo"),
                "confidence": 0.95,
                "affected_files": ["src/main.py"],
                "root_cause": task_data.get("description", "Unknown error"),
                "reasoning": "Placeholder reasoning"
            }

            # Update status to planning
            await self.queue.update_task_status(
                task_id,
                TaskStatus.PLANNING,
                discovery=json.dumps(discovery)
            )

            print(f"  📝 Creating execution plan for {task_id}")
            await asyncio.sleep(2)  # Simulate processing

            # Mock plan results
            plan = {
                "summary": f"Fix for {task_id}",
                "steps": [
                    {"order": 1, "type": "test", "action": "Write test"},
                    {"order": 2, "type": "implement", "action": "Implement fix"}
                ],
                "test_command": "pytest",
                "estimated_minutes": 15,
                "risk_level": "low",
                "risks": ["Minimal risk"]
            }

            # Create draft PR (placeholder)
            pr_url = f"https://github.com/{discovery['repository']}/pull/123"

            # Update status to pending approval
            await self.queue.update_task_status(
                task_id,
                TaskStatus.PENDING_APPROVAL,
                plan=json.dumps(plan),
                plan_url=pr_url
            )

            # Send Slack notification
            await self.slack.send_plan_approval_request(
                task_id=task_id,
                repository=discovery["repository"],
                risk_level=plan["risk_level"],
                estimated_minutes=plan["estimated_minutes"],
                pr_url=pr_url
            )

            # Add GitHub comment
            self.github.add_pr_approval_comment(pr_url, task_id)

            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("planning", "success", duration)

            print(f"✅ Task {task_id} ready for approval")

        except Exception as e:
            print(f"❌ Task {task_id} failed: {e}")
            await self.queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            # Send failure notification
            await self.slack.send_task_failed(task_id, str(e))

            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("planning", "failed", duration)


async def main():
    """Main entry point."""
    worker = PlanningAgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
