"""Database initialization and management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import structlog

from core.config import settings
from .models import Base, SessionDB, TaskDB, EntityDB

logger = structlog.get_logger()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized", url=settings.database_url)


async def get_session() -> AsyncSession:
    """Get database session."""
    async with async_session_factory() as session:
        yield session


__all__ = [
    "Base",
    "SessionDB",
    "TaskDB",
    "EntityDB",
    "engine",
    "async_session_factory",
    "init_db",
    "get_session",
]
