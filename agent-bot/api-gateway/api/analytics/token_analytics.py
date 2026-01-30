from datetime import datetime, timedelta, timezone
import asyncpg
import structlog

from .models import TokenUsageSummary, ModelUsageSummary

logger = structlog.get_logger()


class TokenAnalytics:
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def get_total_tokens(
        self,
        period: str = "day",
        count: int = 7,
    ) -> list[TokenUsageSummary]:
        end = datetime.now(timezone.utc)

        if period == "day":
            delta = timedelta(days=1)
        elif period == "week":
            delta = timedelta(weeks=1)
        elif period == "month":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=1)

        summaries: list[TokenUsageSummary] = []

        for i in range(count):
            period_end = end - (delta * i)
            period_start = period_end - delta

            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        SUM(input_tokens) as total_input,
                        SUM(output_tokens) as total_output,
                        SUM(cost_usd) as total_cost,
                        COUNT(*) as task_count
                    FROM usage_metrics
                    WHERE created_at >= $1 AND created_at < $2
                    """,
                    period_start,
                    period_end,
                )

            if row:
                total_input = row["total_input"] or 0
                total_output = row["total_output"] or 0

                summaries.append(
                    TokenUsageSummary(
                        period=f"{period_start.date()}",
                        total_tokens=total_input + total_output,
                        input_tokens=total_input,
                        output_tokens=total_output,
                        total_cost_usd=float(row["total_cost"] or 0),
                        task_count=row["task_count"],
                    )
                )

        return list(reversed(summaries))

    async def get_tokens_by_model(
        self,
        days: int = 30,
    ) -> list[ModelUsageSummary]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    model,
                    SUM(input_tokens + output_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    COUNT(*) as task_count
                FROM usage_metrics
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY model
                ORDER BY total_tokens DESC
                """,
                start,
                end,
            )

        period = f"last_{days}_days"

        return [
            ModelUsageSummary(
                model=row["model"],
                period=period,
                total_tokens=row["total_tokens"],
                total_cost_usd=float(row["total_cost"]),
                task_count=row["task_count"],
            )
            for row in rows
        ]

    async def get_tokens_by_provider(
        self,
        days: int = 30,
    ) -> dict[str, int]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    provider,
                    SUM(input_tokens + output_tokens) as total_tokens
                FROM usage_metrics
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY provider
                ORDER BY total_tokens DESC
                """,
                start,
                end,
            )

        return {row["provider"]: row["total_tokens"] for row in rows}
