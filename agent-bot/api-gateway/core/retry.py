import asyncio
import structlog
from typing import TypeVar, Callable, Awaitable
from functools import wraps

logger = structlog.get_logger()

T = TypeVar("T")


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay_seconds * (self.exponential_base ** attempt),
            self.max_delay_seconds,
        )

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return delay


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
) -> T:
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt < config.max_attempts - 1:
                delay = config.get_delay(attempt)
                logger.warning(
                    "retry_attempt",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=config.max_attempts,
                    delay_seconds=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "retry_exhausted",
                    operation=operation_name,
                    attempts=config.max_attempts,
                    error=str(e),
                )

    if last_exception:
        raise last_exception

    raise RuntimeError(f"Retry failed for {operation_name}")


def with_retry(
    config: RetryConfig | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(
                func=lambda: func(*args, **kwargs),
                config=config,
                retryable_exceptions=retryable_exceptions,
                operation_name=func.__name__,
            )

        return wrapper

    return decorator
