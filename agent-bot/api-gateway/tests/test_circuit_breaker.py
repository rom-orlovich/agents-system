import pytest
import asyncio
from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
    with_circuit_breaker,
)


@pytest.fixture
def circuit_breaker():
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=0.1,
    )
    return CircuitBreaker("test_circuit", config)


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state_success(circuit_breaker: CircuitBreaker):
    async def successful_operation():
        return "success"

    result = await circuit_breaker.call(successful_operation)

    assert result == "success"
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(circuit_breaker: CircuitBreaker):
    async def failing_operation():
        raise ValueError("Operation failed")

    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.failure_count >= 3


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_calls_when_open(circuit_breaker: CircuitBreaker):
    async def failing_operation():
        raise ValueError("Operation failed")

    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

    assert circuit_breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_operation)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_transition(circuit_breaker: CircuitBreaker):
    async def failing_operation():
        raise ValueError("Operation failed")

    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

    assert circuit_breaker.state == CircuitState.OPEN

    await asyncio.sleep(0.15)

    async def successful_operation():
        return "success"

    result = await circuit_breaker.call(successful_operation)
    assert circuit_breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successes(circuit_breaker: CircuitBreaker):
    async def failing_operation():
        raise ValueError("Operation failed")

    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

    await asyncio.sleep(0.15)

    async def successful_operation():
        return "success"

    await circuit_breaker.call(successful_operation)
    await circuit_breaker.call(successful_operation)

    assert circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_with_fallback(circuit_breaker: CircuitBreaker):
    async def failing_operation():
        raise ValueError("Operation failed")

    async def fallback_operation():
        return "fallback"

    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_operation)

    result = await circuit_breaker.call(failing_operation, fallback=fallback_operation)

    assert result == "fallback"
