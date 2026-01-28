import asyncio
import structlog
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable, Tuple, Type, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from domain.exceptions import RateLimitError, ExternalServiceError

logger = structlog.get_logger()

T = TypeVar("T")

TRANSIENT_ERRORS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    ExternalServiceError,
)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    wait_min: float = 2.0
    wait_max: float = 10.0
    wait_multiplier: float = 1.0
    retry_on: Tuple[Type[Exception], ...] = TRANSIENT_ERRORS

    @classmethod
    def default(cls) -> "RetryPolicy":
        return cls(
            max_attempts=3,
            wait_min=2,
            wait_max=10,
            wait_multiplier=1,
        )

    @classmethod
    def aggressive(cls) -> "RetryPolicy":
        return cls(
            max_attempts=5,
            wait_min=1,
            wait_max=5,
            wait_multiplier=1,
        )

    @classmethod
    def conservative(cls) -> "RetryPolicy":
        return cls(
            max_attempts=2,
            wait_min=5,
            wait_max=30,
            wait_multiplier=2,
        )

    @classmethod
    def no_retry(cls) -> "RetryPolicy":
        return cls(max_attempts=1)


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 2.0,
    wait_max: float = 10.0,
    wait_multiplier: float = 1.0,
    retry_on: Tuple[Type[Exception], ...] = TRANSIENT_ERRORS,
):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_exception = None

            async for attempt_state in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(
                    multiplier=wait_multiplier,
                    min=wait_min,
                    max=wait_max,
                ),
                retry=retry_if_exception_type(retry_on),
                reraise=True,
            ):
                with attempt_state:
                    attempt += 1
                    try:
                        result = await func(*args, **kwargs)
                        if attempt > 1:
                            logger.info(
                                "retry_succeeded",
                                function=func.__name__,
                                attempt=attempt,
                            )
                        return result
                    except retry_on as e:
                        last_exception = e
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def with_rate_limit_handling(
    func: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                if attempt + 1 >= max_attempts:
                    raise

                wait_time = e.retry_after or 5
                logger.warning(
                    "rate_limit_wait",
                    function=func.__name__,
                    wait_seconds=wait_time,
                    attempt=attempt + 1,
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unexpected state in rate limit handler")

    return wrapper


async def github_api_call(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    @with_retry(
        max_attempts=3,
        wait_min=2,
        wait_max=10,
        retry_on=(ConnectionError, TimeoutError, ExternalServiceError),
    )
    async def _call() -> T:
        return await func(*args, **kwargs)

    return await _call()


async def jira_api_call(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    @with_retry(
        max_attempts=3,
        wait_min=2,
        wait_max=15,
        retry_on=(ConnectionError, TimeoutError, ExternalServiceError),
    )
    async def _call() -> T:
        return await func(*args, **kwargs)

    return await _call()


async def slack_api_call(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    @with_retry(
        max_attempts=3,
        wait_min=1,
        wait_max=5,
        retry_on=(ConnectionError, TimeoutError, ExternalServiceError),
    )
    async def _call() -> T:
        return await func(*args, **kwargs)

    return await _call()


class RetryableClient:

    _retry_policy: RetryPolicy = RetryPolicy.default()

    async def _with_retry(
        self,
        coro: Awaitable[T],
        policy: RetryPolicy = None,
    ) -> T:
        policy = policy or self._retry_policy

        @with_retry(
            max_attempts=policy.max_attempts,
            wait_min=policy.wait_min,
            wait_max=policy.wait_max,
            wait_multiplier=policy.wait_multiplier,
            retry_on=policy.retry_on,
        )
        async def _execute() -> T:
            return await coro

        return await _execute()
