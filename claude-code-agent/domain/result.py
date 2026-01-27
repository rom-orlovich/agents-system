"""
Result types for functional error handling.

Instead of raising exceptions for expected error conditions,
use Result[T] to represent either Success[T] or Failure.

Benefits:
- Forces explicit error handling
- Makes error paths visible in type signatures
- Distinguishes recoverable from non-recoverable errors
- Composable with map/flatMap operations
"""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Success(Generic[T]):
    """
    Represents a successful operation result.

    Contains the value of the successful operation.
    """
    value: T

    def is_success(self) -> bool:
        """Check if this is a success."""
        return True

    def is_failure(self) -> bool:
        """Check if this is a failure."""
        return False

    def unwrap(self) -> T:
        """
        Get the success value.

        Returns the contained value.
        """
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default.

        Returns the contained value since this is a success.
        """
        return self.value

    def map(self, fn: Callable[[T], U]) -> "Success[U]":
        """
        Map a function over the success value.

        Returns a new Success with the transformed value.
        """
        return Success(fn(self.value))

    def flat_map(self, fn: Callable[[T], "Result[U]"]) -> "Result[U]":
        """
        FlatMap a function that returns a Result.

        Chains operations that might fail.
        """
        return fn(self.value)


@dataclass
class Failure:
    """
    Represents a failed operation result.

    Contains error information including:
    - error: Human-readable error message
    - error_type: Type/category of the error
    - recoverable: Whether the operation might succeed if retried
    """
    error: str
    error_type: str
    recoverable: bool = True

    def is_success(self) -> bool:
        """Check if this is a success."""
        return False

    def is_failure(self) -> bool:
        """Check if this is a failure."""
        return True

    def unwrap(self) -> None:
        """
        Attempt to get the value.

        Raises ValueError since this is a failure.
        """
        raise ValueError(f"Cannot unwrap Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """
        Get the default value since this is a failure.

        Returns the provided default value.
        """
        return default

    def map(self, fn: Callable[[T], U]) -> "Failure":
        """
        Map a function over the value.

        Returns self unchanged since this is a failure.
        """
        return self

    def flat_map(self, fn: Callable[[T], "Result[U]"]) -> "Failure":
        """
        FlatMap a function.

        Returns self unchanged since this is a failure.
        """
        return self


# Type alias for Result[T]
Result = Union[Success[T], Failure]


def success(value: T) -> Success[T]:
    """Create a Success result."""
    return Success(value)


def failure(error: str, error_type: str = "Error", recoverable: bool = True) -> Failure:
    """Create a Failure result."""
    return Failure(error=error, error_type=error_type, recoverable=recoverable)


def from_exception(e: Exception, recoverable: bool = True) -> Failure:
    """Create a Failure from an exception."""
    return Failure(
        error=str(e),
        error_type=type(e).__name__,
        recoverable=recoverable,
    )


def try_result(fn: Callable[[], T]) -> Result[T]:
    """
    Execute a function and return its result as a Result type.

    If the function succeeds, returns Success[T].
    If the function raises an exception, returns Failure.
    """
    try:
        return Success(fn())
    except Exception as e:
        return from_exception(e)


async def try_result_async(fn: Callable[[], T]) -> Result[T]:
    """
    Execute an async function and return its result as a Result type.

    If the function succeeds, returns Success[T].
    If the function raises an exception, returns Failure.
    """
    try:
        return Success(await fn())
    except Exception as e:
        return from_exception(e)
