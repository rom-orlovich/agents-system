from typing import Any
import time
import redis.asyncio as redis
import structlog
from prometheus_client import Counter, Gauge, Histogram, generate_latest

from config import get_settings

logger = structlog.get_logger(__name__)

TASKS_TOTAL = Counter(
    "agent_tasks_total",
    "Total number of tasks processed",
    ["status", "source"],
)

TASKS_IN_QUEUE = Gauge(
    "agent_tasks_in_queue",
    "Number of tasks currently in queue",
)

TASK_DURATION = Histogram(
    "agent_task_duration_seconds",
    "Task processing duration",
    ["source"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

ACTIVE_WORKERS = Gauge(
    "agent_active_workers",
    "Number of active workers",
)


class MetricsCollector:
    def __init__(self):
        self._settings = get_settings()
        self._redis: redis.Redis | None = None
        self._start_time = time.time()

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._settings.redis_url)
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def collect_metrics(self) -> dict[str, Any]:
        client = await self._get_redis()
        queue_length = await client.llen("agent:tasks")

        TASKS_IN_QUEUE.set(queue_length)

        metrics = {
            "uptime_seconds": time.time() - self._start_time,
            "queue_length": queue_length,
            "tasks_processed": 0,
            "tasks_failed": 0,
        }

        return metrics

    async def get_prometheus_metrics(self) -> bytes:
        await self.collect_metrics()
        return generate_latest()

    def record_task_started(self, source: str) -> None:
        TASKS_TOTAL.labels(status="started", source=source).inc()

    def record_task_completed(self, source: str, duration: float) -> None:
        TASKS_TOTAL.labels(status="completed", source=source).inc()
        TASK_DURATION.labels(source=source).observe(duration)

    def record_task_failed(self, source: str) -> None:
        TASKS_TOTAL.labels(status="failed", source=source).inc()
