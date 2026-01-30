import pytest
import asyncio
from core.retry import RetryConfig, retry_with_backoff, with_retry


@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    call_count = 0

    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    config = RetryConfig(max_attempts=3)
    result = await retry_with_backoff(successful_operation, config)

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_success_after_failures():
    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    config = RetryConfig(max_attempts=3, base_delay_seconds=0.01)
    result = await retry_with_backoff(flaky_operation, config)

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    call_count = 0

    async def always_failing_operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")

    config = RetryConfig(max_attempts=3, base_delay_seconds=0.01)

    with pytest.raises(ValueError, match="Always fails"):
        await retry_with_backoff(
            always_failing_operation, config, retryable_exceptions=(ValueError,)
        )

    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_with_decorator():
    call_count = 0

    @with_retry(config=RetryConfig(max_attempts=3, base_delay_seconds=0.01))
    async def decorated_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Temporary failure")
        return "success"

    result = await decorated_function()

    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_delay_calculation():
    config = RetryConfig(
        max_attempts=5,
        base_delay_seconds=1.0,
        exponential_base=2.0,
        jitter=False,
    )

    delays = [config.get_delay(i) for i in range(5)]

    assert delays[0] == 1.0
    assert delays[1] == 2.0
    assert delays[2] == 4.0
    assert delays[3] == 8.0
    assert delays[4] == 16.0
