import importlib
import asyncpg
from pathlib import Path
from typing import Protocol
import structlog

logger = structlog.get_logger()


class MigrationModule(Protocol):
    MIGRATION_ID: str
    MIGRATION_NAME: str

    async def up(self, connection: asyncpg.Connection) -> None:
        ...

    async def down(self, connection: asyncpg.Connection) -> None:
        ...


class MigrationRunner:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def run_all(self) -> int:
        conn = await asyncpg.connect(self._database_url)
        try:
            await self._ensure_migrations_table(conn)
            applied = await self._get_applied_migrations(conn)
            migrations = self._load_migrations()

            count = 0
            for migration in migrations:
                if migration.MIGRATION_ID in applied:
                    continue

                logger.info(
                    "applying_migration",
                    migration_id=migration.MIGRATION_ID,
                    name=migration.MIGRATION_NAME,
                )

                async with conn.transaction():
                    await migration.up(conn)
                    await self._record_migration(conn, migration.MIGRATION_ID)

                count += 1

            return count
        finally:
            await conn.close()

    async def _ensure_migrations_table(self, conn: asyncpg.Connection) -> None:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

    async def _get_applied_migrations(
        self, conn: asyncpg.Connection
    ) -> set[str]:
        rows = await conn.fetch("SELECT id FROM _migrations")
        return {row["id"] for row in rows}

    async def _record_migration(
        self, conn: asyncpg.Connection, migration_id: str
    ) -> None:
        await conn.execute(
            "INSERT INTO _migrations (id) VALUES ($1)", migration_id
        )

    def _load_migrations(self) -> list[MigrationModule]:
        migrations_dir = Path(__file__).parent / "versions"
        migrations = []

        for path in sorted(migrations_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module_name = f"database.migrations.versions.{path.stem}"
            module = importlib.import_module(module_name)
            migrations.append(module)

        return migrations
