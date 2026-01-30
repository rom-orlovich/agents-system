from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import health
from core.config import settings
from core.database import init_db

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    db_pool = await asyncpg.create_pool(settings.database_url)

    await init_db()

    app.state.redis_client = redis_client
    app.state.db_pool = db_pool

    logger.info(
        "agent_bot_started",
        redis_url=settings.redis_url,
        database_url=settings.database_url.split("@")[-1],
    )

    yield

    await redis_client.close()
    await db_pool.close()

    logger.info("agent_bot_stopped")


app = FastAPI(
    title="Agent Bot",
    description="AI-powered agent bot for GitHub, Jira, Slack, and Sentry",
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

app.include_router(health.router, tags=["health"])

logger.info("application_configured")
