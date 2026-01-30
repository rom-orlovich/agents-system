import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import redis.asyncio as redis
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.ports.queue import QueuePort
from oauth.router import create_oauth_router
from oauth.github import GitHubOAuthHandler
from webhooks.router import create_webhook_router
from webhooks.registry.registry import WebhookRegistry
from webhooks.handlers.github import GitHubWebhookHandler

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
database_url = os.getenv("DATABASE_URL", "postgresql://agent:agent@localhost:5432/agent_bot")
github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")


class RedisQueueAdapter:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._client = redis_client

    async def enqueue(self, message) -> None:
        import json
        from datetime import datetime, timezone

        message_dict = message.model_dump(mode="json")
        message_json = json.dumps(message_dict)
        await self._client.zadd("agent:tasks", {message_json: message.priority.value})

    async def dequeue(self, timeout_seconds: float = 30.0):
        result = await self._client.bzpopmin("agent:tasks", timeout=timeout_seconds)
        if result is None:
            return None

        import json
        from datetime import datetime
        from shared.ports.queue import TaskQueueMessage, TaskPriority

        _, message_json, _ = result
        message_dict = json.loads(message_json)
        message_dict["created_at"] = datetime.fromisoformat(message_dict["created_at"])
        message_dict["priority"] = TaskPriority(message_dict["priority"])
        return TaskQueueMessage.model_validate(message_dict)

    async def ack(self, task_id: str) -> None:
        pass

    async def nack(self, task_id: str) -> None:
        pass

    async def get_queue_size(self) -> int:
        size = await self._client.zcard("agent:tasks")
        return size if isinstance(size, int) else 0


class PostgresInstallationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, data):
        import uuid
        from datetime import datetime, timezone

        installation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO installations (
                    id, platform, organization_id, organization_name,
                    access_token, refresh_token, scopes, webhook_secret,
                    installed_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                installation_id,
                data.platform.value,
                data.organization_id,
                data.organization_name,
                data.access_token,
                data.refresh_token,
                data.scopes,
                data.webhook_secret,
                data.installed_by,
                now,
                now,
            )

        from token_service.models import Installation, Platform

        return Installation(
            id=row["id"],
            platform=Platform(row["platform"]),
            organization_id=row["organization_id"],
            organization_name=row["organization_name"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            scopes=row["scopes"],
            webhook_secret=row["webhook_secret"],
            installed_by=row["installed_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, installation_id: str):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM installations WHERE id = $1",
                installation_id,
            )

        if row is None:
            return None

        from token_service.models import Installation, Platform

        return Installation(
            id=row["id"],
            platform=Platform(row["platform"]),
            organization_id=row["organization_id"],
            organization_name=row["organization_name"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            scopes=row["scopes"],
            webhook_secret=row["webhook_secret"],
            installed_by=row["installed_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_organization(self, platform: str, organization_id: str):
        return None

    async def update(self, installation_id: str, data):
        return None

    async def delete(self, installation_id: str) -> bool:
        return False

    async def list_all(self):
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    db_pool = await asyncpg.create_pool(database_url)

    app.state.redis_client = redis_client
    app.state.db_pool = db_pool
    app.state.queue = RedisQueueAdapter(redis_client)
    app.state.repository = PostgresInstallationRepository(db_pool)

    logger.info(
        "api_gateway_started",
        redis_url=redis_url,
        database_url=database_url.split("@")[-1],
    )

    yield

    await redis_client.close()
    await db_pool.close()

    logger.info("api_gateway_stopped")


app = FastAPI(
    title="Agent Bot API Gateway",
    description="OAuth and webhook management for agent bot",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    from observability import HealthChecker

    checker = HealthChecker(
        redis_client=app.state.redis_client,
        db_pool=app.state.db_pool,
        queue=app.state.queue,
    )

    return await checker.check_all()


@app.get("/metrics")
async def metrics():
    queue_size = await app.state.queue.get_queue_size()

    return {
        "service": "api-gateway",
        "queue_size": queue_size,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


sys.path.insert(0, str(Path(__file__).parent.parent / "agent-container"))

from token_service import TokenService

github_handler = GitHubOAuthHandler(
    client_id=github_client_id,
    client_secret=github_client_secret,
)


@app.on_event("startup")
async def setup_routers():
    token_service = TokenService(repository=app.state.repository)

    oauth_router = create_oauth_router(
        token_service=token_service,
        github_handler=github_handler,
    )
    app.include_router(oauth_router)

    registry = WebhookRegistry()
    registry.register("github", GitHubWebhookHandler())

    webhook_router = create_webhook_router(
        registry=registry,
        queue=app.state.queue,
    )
    app.include_router(webhook_router)

    logger.info("routers_configured", providers=registry.list_providers())
