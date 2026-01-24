"""
Test script to demonstrate the approval flow.

This simulates what happens when a user comments "@agent approve" on a GitHub PR.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.task_queue import RedisQueue
from shared.models import TaskStatus, JiraTask
from shared.enums import TaskSource


async def demo_approval_flow():
    """Demonstrate the complete approval flow."""
    
    queue = RedisQueue()
    
    print("=" * 60)
    print("DEMO: GitHub Approval Flow")
    print("=" * 60)
    
    # Step 1: Simulate a task being created (e.g., from Jira webhook)
    print("\n📥 Step 1: Task created from Jira webhook")
    task = JiraTask(
        task_id="task-jira-KAN-11",
        source=TaskSource.JIRA,
        action="enrich",
        issue_key="KAN-11",
        description="Fix login bug",
        repository="myorg/myapp"
    )
    
    # Push to planning queue
    await queue.push_task("planning_queue", task)
    print(f"   ✓ Task {task.task_id} queued for planning")
    
    # Step 2: Planning agent creates a plan and a PR
    print("\n📝 Step 2: Planning agent creates plan PR #123")
    pr_url = "https://github.com/myorg/myapp/pull/123"
    
    # Register the PR-to-task mapping
    await queue.register_pr_task(
        pr_url=pr_url,
        task_id=task.task_id,
        repository="myorg/myapp",
        pr_number=123
    )
    print(f"   ✓ Registered PR #123 → {task.task_id}")
    
    # Update task status
    await queue.update_task_status(task.task_id, TaskStatus.PENDING_APPROVAL)
    print(f"   ✓ Task status: pending_approval")
    
    # Step 3: User comments "@agent approve" on PR #123
    print("\n💬 Step 3: User comments '@agent approve' on PR #123")
    
    # Webhook looks up task by PR
    found_task_id = await queue.get_task_id_by_pr(123, "myorg/myapp")
    print(f"   ✓ Found task: {found_task_id}")
    
    # Step 4: Webhook approves and queues for execution
    print("\n✅ Step 4: Webhook processes approval")
    await queue.update_task_status(found_task_id, TaskStatus.APPROVED)
    
    # Push to execution queue (using dict for backwards compatibility)
    task_data = await queue.get_task(found_task_id)
    await queue.push("execution_queue", task_data)
    print(f"   ✓ Task approved and queued for execution")
    print(f"   ✓ Webhook adds 👀 reaction to comment")
    
    # Step 5: Executor agent picks up the task
    print("\n⚙️  Step 5: Executor agent processes task")
    print(f"   ✓ Polling execution_queue...")
    
    # Simulate executor picking up task
    exec_task = await queue.pop("execution_queue", timeout=1)
    if exec_task:
        print(f"   ✓ Got task: {exec_task.get('task_id')}")
        print(f"   ✓ Running Claude Code CLI...")
        print(f"   ✓ Agent posts updates via MCP")
    
    # Cleanup
    await queue.delete_task(task.task_id)
    await queue.disconnect()
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_approval_flow())
