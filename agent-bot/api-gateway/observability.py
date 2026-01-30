from typing import Dict
import time
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class HealthChecker:
    def __init__(
        self,
        redis_client: redis.Redis,
        db_pool: asyncpg.Pool,
        queue,
    ) -> None:
        self._redis = redis_client
        self._db_pool = db_pool
        self._queue = queue
        self._start_time = time.time()

    async def check_all(self) -> Dict:
        checks = {}

        checks["redis"] = await self._check_redis()
        checks["database"] = await self._check_database()
        checks["queue"] = await self._check_queue()

        all_healthy = all(check["healthy"] for check in checks.values())

        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": "2.0.0",
            "uptime_seconds": int(time.time() - self._start_time),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }

    async def _check_redis(self) -> Dict:
        try:
            start = time.time()
            await self._redis.ping()
            latency = time.time() - start

            return {
                "healthy": True,
                "latency_ms": round(latency * 1000, 2),
            }
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_database(self) -> Dict:
        try:
            start = time.time()
            async with self._db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            latency = time.time() - start

            return {
                "healthy": True,
                "latency_ms": round(latency * 1000, 2),
            }
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_queue(self) -> Dict:
        try:
            size = await self._queue.get_queue_size()
            return {
                "healthy": True,
                "queue_size": size,
            }
        except Exception as e:
            logger.error("queue_health_check_failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
            }


class MetricsCollector:
    def __init__(self) -> None:
        self._request_count = 0
        self._webhook_count_by_provider: Dict[str, int] = {}
        self._task_count = 0

    def record_request(self) -> None:
        self._request_count += 1

    def record_webhook(self, provider: str) -> None:
        self._webhook_count_by_provider[provider] = (
            self._webhook_count_by_provider.get(provider, 0) + 1
        )
        self._task_count += 1

    def get_metrics(self) -> Dict:
        return {
            "total_requests": self._request_count,
            "webhooks_by_provider": self._webhook_count_by_provider,
            "total_tasks_created": self._task_count,
        }
