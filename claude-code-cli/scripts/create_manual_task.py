
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.task_queue import RedisQueue
from shared.models import GitHubTask, TaskSource, TaskStatus
from shared.config import settings
from shared.token_manager import TokenManager

async def create_manual_task():
    queue = RedisQueue()
    await queue.connect()
    
    # Generate ID
    task_id = f"manual-task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Get Real User ID from TokenManager (uses local credentials)
    # This ensures the task matches the user's actual session
    token_manager = TokenManager()
    try:
        await token_manager.load_credentials()
        account_id = token_manager.get_account_id()
        email = "unknown@example.com"
        # Try to guess email or user info if not in credentials
        # (Credentials usually just have tokens, but we can check if there's any other file)
        print(f"👤 Detected Account ID: {account_id}")
    except Exception as e:
        print(f"⚠️ Could not load credentials: {e}")
        account_id = "manual_user"

    print(f"🚀 Creating manual GitHub task: {task_id}")

    queue_name = settings.PLANNING_QUEUE
    
    # Create 3 tasks to ensure visibility
    for i in range(1, 4):
        t_id = f"{task_id}_{i}"
        
        # Create each task
        t = GitHubTask(
            task_id=t_id,
            source=TaskSource.GITHUB,
            status=TaskStatus.QUEUED,
            repository="rom-orlovich/agents-system",
            action="discover",
            comment=f"Manual discovery task #{i}",
            pr_url="https://github.com/rom-orlovich/agents-system"
        )
        
        await queue.push_task(queue_name, t)
        
        # Inject account_id
        await queue.redis.hset(
            f"tasks:{t_id}",
            mapping={
                "account_id": account_id,
                "email": "you@example.com",
                # Make one active for variety
                "status": TaskStatus.EXECUTING.value if i == 1 else TaskStatus.QUEUED.value
            }
        )
        print(f"✅ Created task {t_id}")

    print("💾 Forcing Redis SAVE to disk...")
    await queue.redis.save()
    
    print(f"🆔 Base Task ID: {task_id}")
    print(f"👤 Account ID linked: {account_id}")
    print("\nCheck the dashboard now.")
    
    await queue.disconnect()

if __name__ == "__main__":
    asyncio.run(create_manual_task())
