from fastapi import APIRouter
from fastapi.responses import Response

from services import MetricsCollector

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
metrics_collector = MetricsCollector()


@router.get("")
async def get_metrics():
    return await metrics_collector.collect_metrics()


@router.get("/prometheus")
async def get_prometheus_metrics():
    metrics = await metrics_collector.get_prometheus_metrics()
    return Response(
        content=metrics,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
