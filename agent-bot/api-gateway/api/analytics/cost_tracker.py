from datetime import datetime, timedelta, timezone
from typing import Literal
import uuid
import asyncpg
import structlog

from .models import UsageMetric, CostSummary

logger = structlog.get_logger()


class CostTracker:
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def record_usage(
        self,
        task_id: str,
        installation_id: str,
        provider: Literal["github", "jira", "slack", "sentry"],
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        duration_seconds: float,
    ) -> UsageMetric:
        metric_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO usage_metrics (
                    id, task_id, installation_id, provider,
                    model, input_tokens, output_tokens,
                    cost_usd, duration_seconds, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                metric_id,
                task_id,
                installation_id,
                provider,
                model,
                input_tokens,
                output_tokens,
                cost_usd,
                duration_seconds,
                now,
            )

        logger.info(
            "usage_recorded",
            task_id=task_id,
            cost_usd=cost_usd,
            tokens=input_tokens + output_tokens,
        )

        return UsageMetric(
            id=metric_id,
            task_id=task_id,
            installation_id=installation_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_seconds=duration_seconds,
            created_at=now,
        )

    async def get_cost_by_period(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CostSummary]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    i.organization_id,
                    SUM(um.cost_usd) as total_cost,
                    COUNT(*) as task_count,
                    AVG(um.cost_usd) as avg_cost
                FROM usage_metrics um
                JOIN installations i ON um.installation_id = i.id
                WHERE um.created_at >= $1 AND um.created_at <= $2
                GROUP BY i.organization_id
                ORDER BY total_cost DESC
                """,
                start,
                end,
            )

        period = f"{start.date()}_to_{end.date()}"

        return [
            CostSummary(
                organization_id=row["organization_id"],
                period=period,
                total_cost_usd=float(row["total_cost"]),
                task_count=row["task_count"],
                average_cost_per_task=float(row["avg_cost"]),
            )
            for row in rows
        ]

    async def get_cost_by_organization(
        self,
        organization_id: str,
        days: int = 30,
    ) -> CostSummary:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    SUM(um.cost_usd) as total_cost,
                    COUNT(*) as task_count,
                    AVG(um.cost_usd) as avg_cost
                FROM usage_metrics um
                JOIN installations i ON um.installation_id = i.id
                WHERE i.organization_id = $1
                  AND um.created_at >= $2
                  AND um.created_at <= $3
                """,
                organization_id,
                start,
                end,
            )

        if row is None or row["total_cost"] is None:
            return CostSummary(
                organization_id=organization_id,
                period=f"last_{days}_days",
                total_cost_usd=0.0,
                task_count=0,
                average_cost_per_task=0.0,
            )

        return CostSummary(
            organization_id=organization_id,
            period=f"last_{days}_days",
            total_cost_usd=float(row["total_cost"]),
            task_count=row["task_count"],
            average_cost_per_task=float(row["avg_cost"]),
        )
