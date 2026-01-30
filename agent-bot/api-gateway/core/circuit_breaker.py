import asyncio
import time
import structlog
from typing import TypeVar, Callable, Awaitable
from functools import wraps
from enum import Enum

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerConfig:
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
        self.logger = structlog.get_logger(circuit_breaker=name)

    async def call(
        self, func: Callable[[], Awaitable[T]], fallback: Callable[[], Awaitable[T]] | None = None
    ) -> T:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                self.logger.warning("circuit_breaker_open", name=self.name)
                if fallback:
                    return await fallback()
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.logger.warning("circuit_breaker_half_open_limit", name=self.name)
                if fallback:
                    return await fallback()
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is HALF_OPEN with max calls reached"
                )

        try:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

            result = await func()

            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout_seconds

    def _transition_to_half_open(self) -> None:
        self.logger.info("circuit_breaker_half_open", name=self.name)
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.config.failure_threshold
        ):
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        self.logger.warning(
            "circuit_breaker_opened",
            name=self.name,
            failure_count=self.failure_count,
        )
        self.state = CircuitState.OPEN

    def _transition_to_closed(self) -> None:
        self.logger.info("circuit_breaker_closed", name=self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0


class CircuitBreakerOpenError(Exception):
    pass


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig()
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def with_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
    fallback: Callable[..., Awaitable[T]] | None = None,
):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            circuit_breaker = get_circuit_breaker(name, config)
            return await circuit_breaker.call(
                lambda: func(*args, **kwargs),
                fallback=fallback if fallback else None,
            )

        return wrapper

    return decorator
