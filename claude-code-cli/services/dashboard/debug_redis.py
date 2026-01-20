
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/app")
sys.path.insert(0, "/")

from shared.task_queue import RedisQueue
from shared.config import settings

async def check_redis():
    print(f"Connecting to Redis at: {settings.REDIS_URL}")
    queue = RedisQueue()
    await queue.connect()
    
    print("Checking keys...")
    keys = await queue.redis.keys("tasks:*")
    print(f"Found {len(keys)} keys: {keys}")
    
    print("Fetching all tasks...")
    tasks = await queue.get_all_tasks()
    print(f"Retrieved {len(tasks)} tasks via get_all_tasks()")
    
    for t in tasks:
        print(f"Task: {t.get('task_id')} | Account: {t.get('account_id')}")

    await queue.disconnect()

if __name__ == "__main__":
    asyncio.run(check_redis())
