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
    """Initialize database tables and run migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run migrations for missing columns (safe - only adds if missing)
    await migrate_conversations_table()
    await migrate_tasks_table()

    logger.info("Database initialized", url=settings.database_url)


async def migrate_conversations_table() -> None:
    """Migrate conversations table to add missing columns if needed."""
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            columns_to_add = [
                ("initiated_task_id", "VARCHAR(255)"),
                ("flow_id", "VARCHAR(255)"),
                ("total_cost_usd", "REAL NOT NULL DEFAULT 0.0"),
                ("total_tasks", "INTEGER NOT NULL DEFAULT 0"),
                ("total_duration_seconds", "REAL NOT NULL DEFAULT 0.0"),
                ("started_at", "TIMESTAMP"),
                ("completed_at", "TIMESTAMP"),
            ]

            for column_name, column_def in columns_to_add:
                try:
                    # Try to query the column - if it exists, this will succeed
                    await conn.execute(
                        text(f"SELECT {column_name} FROM conversations LIMIT 1")
                    )
                    # Column exists, skip
                except Exception:
                    # Column doesn't exist, add it
                    try:
                        await conn.execute(
                            text(
                                f"ALTER TABLE conversations ADD COLUMN {column_name} {column_def}"
                            )
                        )
                        logger.info(
                            "Added missing column",
                            table="conversations",
                            column=column_name,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to add column",
                            table="conversations",
                            column=column_name,
                            error=str(e),
                        )

            # Create index on flow_id if it doesn't exist
            try:
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_conversations_flow_id ON conversations(flow_id)"
                    )
                )
            except Exception:
                pass  # Index might already exist

    except Exception as e:
        logger.warning("Migration check failed", error=str(e))
        # Don't fail startup if migration check fails


async def migrate_tasks_table() -> None:
    """Migrate tasks table to add missing columns if needed."""
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            columns_to_add = [
                ("initiated_task_id", "VARCHAR(255)"),
                ("flow_id", "VARCHAR(255)"),
            ]

            for column_name, column_def in columns_to_add:
                try:
                    # Try to query the column - if it exists, this will succeed
                    await conn.execute(text(f"SELECT {column_name} FROM tasks LIMIT 1"))
                    # Column exists, skip
                except Exception:
                    # Column doesn't exist, add it
                    try:
                        await conn.execute(
                            text(
                                f"ALTER TABLE tasks ADD COLUMN {column_name} {column_def}"
                            )
                        )
                        logger.info(
                            "Added missing column", table="tasks", column=column_name
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to add column",
                            table="tasks",
                            column=column_name,
                            error=str(e),
                        )

            # Create index on flow_id if it doesn't exist
            try:
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_tasks_flow_id ON tasks(flow_id)"
                    )
                )
            except Exception:
                pass  # Index might already exist

    except Exception as e:
        logger.warning("Migration check for tasks failed", error=str(e))


async def shutdown_db() -> None:
    """Shutdown database engine."""
    await engine.dispose()
    logger.info("Database engine disposed")


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
    "shutdown_db",
    "get_session",
]
