from datetime import datetime, timezone
from uuid import uuid4
import json

import asyncpg
import structlog

from ..models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from ..exceptions import (
    InstallationNotFoundError,
    DuplicateInstallationError,
)

logger = structlog.get_logger()

INSERT_QUERY = """
    INSERT INTO installations (
        id, platform, organization_id, organization_name,
        access_token, refresh_token, token_expires_at,
        scopes, webhook_secret, installed_at, installed_by,
        metadata, is_active
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
    )
    RETURNING *
"""

SELECT_BY_ID_QUERY = "SELECT * FROM installations WHERE id = $1"
SELECT_BY_PLATFORM_ORG_QUERY = "SELECT * FROM installations WHERE platform = $1 AND organization_id = $2"
DELETE_QUERY = "DELETE FROM installations WHERE id = $1"


class PostgresInstallationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, data: InstallationCreate) -> Installation:
        installation_id = f"inst-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    INSERT_QUERY,
                    installation_id,
                    data.platform.value,
                    data.organization_id,
                    data.organization_name,
                    data.access_token,
                    data.refresh_token,
                    data.token_expires_at,
                    data.scopes,
                    data.webhook_secret,
                    now,
                    data.installed_by,
                    json.dumps(data.metadata),
                    True,
                )
        except Exception as e:
            if "unique_violation" in str(e):
                raise DuplicateInstallationError(
                    data.platform.value, data.organization_id
                )
            raise

        return self._row_to_installation(row)

    async def get_by_id(self, installation_id: str) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(SELECT_BY_ID_QUERY, installation_id)

        if row is None:
            return None

        return self._row_to_installation(row)

    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                SELECT_BY_PLATFORM_ORG_QUERY,
                platform.value,
                organization_id,
            )

        if row is None:
            return None

        return self._row_to_installation(row)

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation:
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            existing = await self.get_by_id(installation_id)
            if existing is None:
                raise InstallationNotFoundError("unknown", installation_id)
            return existing

        set_clauses = []
        values = []
        for i, (key, value) in enumerate(update_fields.items(), start=1):
            set_clauses.append(f"{key} = ${i}")
            values.append(value)

        values.append(installation_id)
        query = f"""
            UPDATE installations 
            SET {", ".join(set_clauses)}
            WHERE id = ${len(values)}
            RETURNING *
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)

        if row is None:
            raise InstallationNotFoundError("unknown", installation_id)

        return self._row_to_installation(row)

    async def find(self, filter_: InstallationFilter) -> list[Installation]:
        conditions = []
        values = []
        param_index = 1

        if filter_.platform:
            conditions.append(f"platform = ${param_index}")
            values.append(filter_.platform.value)
            param_index += 1

        if filter_.organization_id:
            conditions.append(f"organization_id = ${param_index}")
            values.append(filter_.organization_id)
            param_index += 1

        if filter_.is_active is not None:
            conditions.append(f"is_active = ${param_index}")
            values.append(filter_.is_active)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT * FROM installations WHERE {where_clause}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *values)

        return [self._row_to_installation(row) for row in rows]

    async def delete(self, installation_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(DELETE_QUERY, installation_id)

        return result == "DELETE 1"

    def _row_to_installation(self, row: asyncpg.Record) -> Installation:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Installation(
            id=row["id"],
            platform=Platform(row["platform"]),
            organization_id=row["organization_id"],
            organization_name=row["organization_name"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            token_expires_at=row["token_expires_at"],
            scopes=row["scopes"],
            webhook_secret=row["webhook_secret"],
            installed_at=row["installed_at"],
            installed_by=row["installed_by"],
            metadata=metadata,
            is_active=row["is_active"],
        )
