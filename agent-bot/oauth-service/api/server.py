from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings

logger = structlog.get_logger(__name__)

engine = None
async_session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global engine, async_session_factory

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("database_connected", url=settings.database_url[:30] + "...")
    yield

    await engine.dispose()
    logger.info("database_disconnected")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")

    async with async_session_factory() as session:
        yield session


def create_app() -> FastAPI:
    app = FastAPI(
        title="OAuth Service",
        description="Multi-tenant OAuth installation service",
        version="1.0.0",
        lifespan=lifespan,
    )

    from .routes import router

    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return app
