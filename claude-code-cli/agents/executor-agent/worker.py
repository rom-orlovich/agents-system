"""Executor Agent queue worker."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from task_queue import RedisQueue
from slack_client import SlackClient
from metrics import metrics


class ExecutorAgentWorker:
    """Executor Agent queue worker."""

    def __init__(self):
        """Initialize worker."""
        self.queue = RedisQueue()
        self.slack = SlackClient()
        self.queue_name = settings.EXECUTION_QUEUE

    async def run(self):
        """Main worker loop."""
        print(f"🚀 Executor Agent Worker started")
        print(f"📥 Listening on queue: {self.queue_name}")

        while True:
            try:
                # Wait for approved task from queue
                task_data = await self.queue.pop(self.queue_name, timeout=0)

                if task_data:
                    await self.process_task(task_data)

            except Exception as e:
                print(f"❌ Error in worker loop: {e}")
                metrics.record_error("executor", "worker_loop")
                await asyncio.sleep(5)

    async def process_task(self, task_data: dict):
        """Process execution task.

        Args:
            task_data: Task data from queue
        """
        task_id = task_data.get("task_id")
        start_time = datetime.now()

        print(f"⚙️ Executing task: {task_id}")
        metrics.record_task_started("executor")

        try:
            # Update status to executing
            await self.queue.update_task_status(
                task_id,
                TaskStatus.EXECUTING
            )

            # Send Slack notification
            repository = task_data.get("discovery", {}).get("repository", "unknown")
            await self.slack.send_execution_started(task_id, repository)

            # Simulate execution (placeholder)
            print(f"  🔄 Running TDD workflow for {task_id}")
            await asyncio.sleep(5)  # Simulate execution

            # Mock results
            pr_url = task_data.get("plan_url", "https://github.com/example/repo/pull/123")
            execution_time = f"{(datetime.now() - start_time).total_seconds():.1f}s"

            # Update status to completed
            await self.queue.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                completed_at=datetime.utcnow().isoformat()
            )

            # Send completion notification
            await self.slack.send_task_completed(
                task_id,
                repository,
                pr_url,
                execution_time
            )

            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("executor", "success", duration)

            print(f"✅ Task {task_id} completed")

        except Exception as e:
            print(f"❌ Task {task_id} failed: {e}")
            await self.queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

            await self.slack.send_task_failed(task_id, str(e))

            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_task_completed("executor", "failed", duration)


async def main():
    """Main entry point."""
    worker = ExecutorAgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
