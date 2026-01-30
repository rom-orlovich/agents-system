from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
from typing import TypeVar, Callable, Awaitable
import time
import structlog

logger = structlog.get_logger()

T = TypeVar("T")

webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total webhook requests received",
    ["provider", "status"],
)

task_processing_duration_seconds = Histogram(
    "task_processing_duration_seconds",
    "Task processing duration in seconds",
    ["status"],
)

tasks_in_queue = Gauge(
    "tasks_in_queue",
    "Number of tasks currently in queue",
)

api_call_duration_seconds = Histogram(
    "api_call_duration_seconds",
    "API call duration in seconds",
    ["service", "endpoint", "status"],
)

cli_execution_cost_usd = Counter(
    "cli_execution_cost_usd",
    "Total cost of CLI executions in USD",
)

cli_execution_tokens = Counter(
    "cli_execution_tokens",
    "Total tokens used in CLI executions",
    ["type"],
)


def track_webhook_request(provider: str, status: str) -> None:
    webhook_requests_total.labels(provider=provider, status=status).inc()


def track_task_duration(status: str, duration_seconds: float) -> None:
    task_processing_duration_seconds.labels(status=status).observe(duration_seconds)


def update_queue_size(size: int) -> None:
    tasks_in_queue.set(size)


def track_api_call(service: str, endpoint: str, status: str, duration_seconds: float) -> None:
    api_call_duration_seconds.labels(
        service=service, endpoint=endpoint, status=status
    ).observe(duration_seconds)


def track_cli_cost(cost_usd: float, input_tokens: int, output_tokens: int) -> None:
    cli_execution_cost_usd.inc(cost_usd)
    cli_execution_tokens.labels(type="input").inc(input_tokens)
    cli_execution_tokens.labels(type="output").inc(output_tokens)


def with_metrics(
    metric_type: str = "api_call", service: str = "unknown", endpoint: str = "unknown"
):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                if metric_type == "api_call":
                    track_api_call(service, endpoint, status, duration)
                elif metric_type == "task":
                    track_task_duration(status, duration)

        return wrapper

    return decorator


def get_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
