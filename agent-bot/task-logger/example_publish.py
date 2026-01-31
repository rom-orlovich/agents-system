import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as redis


async def publish_example_events():
    redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

    webhook_event_id = "webhook-001"
    task_id = "task-001"

    print("Publishing example events...")

    await redis_client.xadd(
        "task_events",
        {
            "type": "webhook:received",
            "webhook_event_id": webhook_event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps({"provider": "github", "payload": {"action": "opened"}}),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "webhook:validated",
            "webhook_event_id": webhook_event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps({"valid": True}),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "webhook:matched",
            "webhook_event_id": webhook_event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps({"command": "approve", "matched": True}),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "webhook:task_created",
            "webhook_event_id": webhook_event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(
                {"task_id": task_id, "command": "approve", "agent": "executor"}
            ),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "task:created",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(
                {
                    "source": "webhook",
                    "assigned_agent": "executor",
                    "input_message": "Fix the authentication bug",
                }
            ),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "task:started",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps({"started_at": datetime.now(timezone.utc).isoformat()}),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "task:output",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps({"content": "I found the bug in login.py"}),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "task:user_input",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(
                {"content": "Yes, please fix it", "question_type": "approval"}
            ),
        },
    )

    await asyncio.sleep(0.1)

    await redis_client.xadd(
        "task_events",
        {
            "type": "task:completed",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(
                {
                    "result": "Fixed authentication bug. Created PR #456.",
                    "cost_usd": 0.0234,
                    "duration_seconds": 145.3,
                }
            ),
        },
    )

    await redis_client.close()
    print(f"✅ Published 9 events for task {task_id}")
    print(f"   View logs at: curl http://localhost:8090/tasks/{task_id}/logs")


if __name__ == "__main__":
    asyncio.run(publish_example_events())
