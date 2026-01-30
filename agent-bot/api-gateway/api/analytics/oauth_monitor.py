from datetime import datetime, timedelta, timezone
import asyncpg
import structlog

from .models import OAuthTokenStatus

logger = structlog.get_logger()


class OAuthMonitor:
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def track_token_usage(
        self,
        installation_id: str,
    ) -> None:
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE installations
                SET last_used_at = $1
                WHERE id = $2
                """,
                now,
                installation_id,
            )

        logger.info(
            "token_usage_tracked",
            installation_id=installation_id,
        )

    async def get_expiring_tokens(
        self,
        days: int = 7,
    ) -> list[OAuthTokenStatus]:
        expiry_threshold = datetime.now(timezone.utc) + timedelta(days=days)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    platform,
                    organization_id,
                    token_expires_at,
                    last_used_at
                FROM installations
                WHERE token_expires_at IS NOT NULL
                  AND token_expires_at <= $1
                ORDER BY token_expires_at ASC
                """,
                expiry_threshold,
            )

        return [
            OAuthTokenStatus(
                installation_id=row["id"],
                platform=row["platform"],
                organization_id=row["organization_id"],
                is_expired=row["token_expires_at"] < datetime.now(timezone.utc),
                expires_at=row["token_expires_at"],
                last_used_at=row["last_used_at"],
            )
            for row in rows
        ]

    async def get_token_status(
        self,
        installation_id: str,
    ) -> OAuthTokenStatus | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    id,
                    platform,
                    organization_id,
                    token_expires_at,
                    last_used_at
                FROM installations
                WHERE id = $1
                """,
                installation_id,
            )

        if row is None:
            return None

        now = datetime.now(timezone.utc)
        is_expired = False

        if row["token_expires_at"]:
            is_expired = row["token_expires_at"] < now

        return OAuthTokenStatus(
            installation_id=row["id"],
            platform=row["platform"],
            organization_id=row["organization_id"],
            is_expired=is_expired,
            expires_at=row["token_expires_at"],
            last_used_at=row["last_used_at"],
        )

    async def trigger_refresh(
        self,
        installation_id: str,
    ) -> bool:
        logger.info(
            "oauth_refresh_triggered",
            installation_id=installation_id,
        )

        return True
