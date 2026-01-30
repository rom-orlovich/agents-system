import uuid
from datetime import datetime, timezone
from typing import Protocol

import asyncpg
import structlog

from shared import Installation, InstallationCreate, InstallationUpdate, Platform

logger = structlog.get_logger()


class InstallationRepository(Protocol):
    async def create(self, data: InstallationCreate) -> Installation: ...

    async def get_by_id(self, installation_id: str) -> Installation | None: ...

    async def get_by_organization(
        self, platform: str, organization_id: str
    ) -> Installation | None: ...

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation | None: ...

    async def delete(self, installation_id: str) -> bool: ...

    async def list_all(self) -> list[Installation]: ...


class PostgresInstallationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, data: InstallationCreate) -> Installation:
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

        return self._row_to_installation(row)

    async def get_by_id(self, installation_id: str) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM installations WHERE id = $1",
                installation_id,
            )

        if row is None:
            return None

        return self._row_to_installation(row)

    async def get_by_organization(
        self, platform: str, organization_id: str
    ) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM installations
                WHERE platform = $1 AND organization_id = $2
                """,
                platform,
                organization_id,
            )

        if row is None:
            return None

        return self._row_to_installation(row)

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation | None:
        updates = []
        values = []
        param_count = 1

        if data.access_token is not None:
            updates.append(f"access_token = ${param_count}")
            values.append(data.access_token)
            param_count += 1

        if data.refresh_token is not None:
            updates.append(f"refresh_token = ${param_count}")
            values.append(data.refresh_token)
            param_count += 1

        if data.scopes is not None:
            updates.append(f"scopes = ${param_count}")
            values.append(data.scopes)
            param_count += 1

        if data.webhook_secret is not None:
            updates.append(f"webhook_secret = ${param_count}")
            values.append(data.webhook_secret)
            param_count += 1

        if not updates:
            return await self.get_by_id(installation_id)

        updates.append(f"updated_at = ${param_count}")
        values.append(datetime.now(timezone.utc))
        param_count += 1

        values.append(installation_id)

        query = f"""
            UPDATE installations
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING *
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)

        if row is None:
            return None

        return self._row_to_installation(row)

    async def delete(self, installation_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM installations WHERE id = $1",
                installation_id,
            )

        return result == "DELETE 1"

    async def list_all(self) -> list[Installation]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM installations")

        return [self._row_to_installation(row) for row in rows]

    def _row_to_installation(self, row: asyncpg.Record) -> Installation:
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
