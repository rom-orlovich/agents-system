
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/app")
sys.path.insert(0, "/")

from shared.task_queue import RedisQueue
from shared.config import settings

async def write_redis():
    print(f"Connecting to Redis at: {settings.REDIS_URL}")
    queue = RedisQueue()
    await queue.connect()
    
    print("Setting key 'dashboard_test'...")
    await queue.redis.set("dashboard_test", "hello from dashboard")
    
    print("Reading key 'dashboard_test'...")
    val = await queue.redis.get("dashboard_test")
    print(f"Value: {val}")

    await queue.disconnect()

if __name__ == "__main__":
    asyncio.run(write_redis())
