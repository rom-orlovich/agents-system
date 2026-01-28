from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Success(Generic[T]):
    value: T

    def is_success(self) -> bool:
        return True

    def is_failure(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> "Success[U]":
        return Success(fn(self.value))

    def flat_map(self, fn: Callable[[T], "Result[U]"]) -> "Result[U]":
        return fn(self.value)


@dataclass
class Failure:
    error: str
    error_type: str
    recoverable: bool = True

    def is_success(self) -> bool:
        return False

    def is_failure(self) -> bool:
        return True

    def unwrap(self) -> None:
        raise ValueError(f"Cannot unwrap Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def map(self, fn: Callable[[T], U]) -> "Failure":
        return self

    def flat_map(self, fn: Callable[[T], "Result[U]"]) -> "Failure":
        return self


Result = Union[Success[T], Failure]


def success(value: T) -> Success[T]:
    return Success(value)


def failure(error: str, error_type: str = "Error", recoverable: bool = True) -> Failure:
    return Failure(error=error, error_type=error_type, recoverable=recoverable)


def from_exception(e: Exception, recoverable: bool = True) -> Failure:
    return Failure(
        error=str(e),
        error_type=type(e).__name__,
        recoverable=recoverable,
    )


def try_result(fn: Callable[[], T]) -> Result[T]:
    try:
        return Success(fn())
    except Exception as e:
        return from_exception(e)


async def try_result_async(fn: Callable[[], T]) -> Result[T]:
    try:
        return Success(await fn())
    except Exception as e:
        return from_exception(e)
