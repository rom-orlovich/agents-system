"""Prometheus metrics collection."""

from typing import Literal
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY


class MetricsCollector:
    """Centralized metrics collector for Prometheus."""

    def __init__(self, service_name: str, registry: CollectorRegistry = REGISTRY) -> None:
        self.service_name = service_name
        self.registry = registry

        self.http_requests_total = Counter(
            f"{service_name}_http_requests_total",
            "Total HTTP requests",
            labelnames=["method", "endpoint", "status"],
            registry=registry,
        )

        self.http_request_duration_seconds = Histogram(
            f"{service_name}_http_request_duration_seconds",
            "HTTP request duration in seconds",
            labelnames=["method", "endpoint"],
            registry=registry,
        )

        self.tasks_total = Counter(
            f"{service_name}_tasks_total",
            "Total tasks processed",
            labelnames=["status", "task_type"],
            registry=registry,
        )

        self.tasks_duration_seconds = Histogram(
            f"{service_name}_tasks_duration_seconds",
            "Task processing duration in seconds",
            labelnames=["task_type"],
            registry=registry,
        )

        self.tasks_in_queue = Gauge(
            f"{service_name}_tasks_in_queue",
            "Number of tasks currently in queue",
            labelnames=["queue_name"],
            registry=registry,
        )

        self.active_connections = Gauge(
            f"{service_name}_active_connections",
            "Number of active connections",
            labelnames=["connection_type"],
            registry=registry,
        )

    def record_http_request(
        self, method: str, endpoint: str, status: int, duration: float
    ) -> None:
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    def record_task(
        self, status: Literal["completed", "failed"], task_type: str, duration: float
    ) -> None:
        """Record task processing metrics."""
        self.tasks_total.labels(status=status, task_type=task_type).inc()
        self.tasks_duration_seconds.labels(task_type=task_type).observe(duration)

    def set_queue_size(self, queue_name: str, size: int) -> None:
        """Set current queue size."""
        self.tasks_in_queue.labels(queue_name=queue_name).set(size)

    def set_active_connections(self, connection_type: str, count: int) -> None:
        """Set active connection count."""
        self.active_connections.labels(connection_type=connection_type).set(count)
