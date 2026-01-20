
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/app")
sys.path.insert(0, "/")

from shared.task_queue import RedisQueue
from shared.config import settings

async def check_redis_v2():
    print(f"Connecting to Redis at: {settings.REDIS_URL}")
    queue = RedisQueue()
    await queue.connect()
    
    print("Listing ALL keys in DB 0...")
    keys = await queue.redis.keys("*")
    print(f"ALL KEYS: {keys}")
    
    print("Testing scan_iter('tasks:*')...")
    scanned_keys = []
    async for k in queue.redis.scan_iter("tasks:*"):
        scanned_keys.append(k)
    print(f"SCAN KEYS: {scanned_keys}")

    await queue.disconnect()

if __name__ == "__main__":
    asyncio.run(check_redis_v2())
