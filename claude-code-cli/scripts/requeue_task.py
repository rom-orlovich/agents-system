import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.task_queue import RedisQueue
from shared.models import TaskStatus

async def requeue_task(task_id: str):
    q = RedisQueue()
    await q.connect()
    
    # Get task data
    task_info = await q.redis.hget(f"tasks:{task_id}", "data")
    if not task_info:
        print(f"Task {task_id} not found")
        return
        
    queue_name = await q.redis.hget(f"tasks:{task_id}", "queue")
    if not queue_name:
        queue_name = "execution_queue"
        
    # Push back to queue
    await q.redis.lpush(queue_name, task_info)
    
    # Update status
    await q.update_task_status(task_id, TaskStatus.QUEUED)
    
    print(f"Task {task_id} pushed back to {queue_name} and set to QUEUED")
    await q.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/requeue_task.py <task_id>")
        sys.exit(1)
    
    asyncio.run(requeue_task(sys.argv[1]))
