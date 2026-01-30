# Testing Guide

## Test Requirements

### Speed
- ✅ Tests MUST run fast (< 5 seconds per test file)
- ✅ Use mocks for external dependencies
- ❌ NO real network calls
- ❌ NO time.sleep() in tests

### Quality
- ✅ Tests MUST pass gracefully
- ✅ NO flaky tests
- ✅ 100% type coverage
- ✅ Use `pytest-asyncio` for async tests

## Running Tests

### Install Dependencies

```bash
# API Gateway
cd api-gateway
pip install -e ".[dev]"
pytest tests/ -v

# Agent Container
cd agent-container
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
pytest tests/ -v

# Integrations (Packages)
cd integrations/packages/jira_client
uv sync
uv run pytest tests/ -v

cd ../slack_client
uv sync
uv run pytest tests/ -v

cd ../sentry_client
uv sync
uv run pytest tests/ -v
```

### Run All Tests

```bash
# From root
./scripts/run-all-tests.sh
```

### Run with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Run Fast Tests Only

```bash
pytest tests/ -v --durations=10
```

## Test Structure

### Example Test File

```python
import pytest
from unittest.mock import AsyncMock
from mymodule import MyClass

@pytest.fixture
def mock_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_success_case(mock_client):
    """Test successful execution."""
    result = await MyClass(mock_client).execute()

    assert result.success is True
    assert result.data is not None

@pytest.mark.asyncio
async def test_failure_case(mock_client):
    """Test error handling."""
    mock_client.call.side_effect = Exception("API Error")

    with pytest.raises(MyException) as exc_info:
        await MyClass(mock_client).execute()

    assert "API Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_validation_error():
    """Test input validation."""
    with pytest.raises(ValidationError):
        InvalidInput(field="")
```

## Mocking Strategies

### HTTP Requests with httpx

```python
import pytest
import httpx
import respx

@pytest.mark.asyncio
@respx.mock
async def test_http_call():
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        assert response.json() == {"status": "ok"}
```

### Async Functions

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_function():
    mock_func = AsyncMock(return_value={"result": "success"})
    result = await mock_func()
    assert result["result"] == "success"
```

### Redis

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get.return_value = '{"task_id": "123"}'
    redis.set.return_value = True
    return redis

@pytest.mark.asyncio
async def test_redis_operations(mock_redis):
    await mock_redis.set("key", "value")
    value = await mock_redis.get("key")
    assert value is not None
```

### Database (PostgreSQL)

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_database_operation(async_session):
    task = Task(task_id="test-123", status="pending")
    async_session.add(task)
    await async_session.commit()

    result = await async_session.get(Task, task.id)
    assert result.task_id == "test-123"
```

## Integration Tests

### Example Integration Test

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_webhook_flow():
    """Test complete webhook flow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Post webhook
        response = await client.post(
            "/webhooks/github",
            json={"action": "created", "issue": {"number": 42}},
            headers={"X-Hub-Signature-256": "sha256=..."}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "task_id" in data
```

## Performance Tests

### Example Performance Test

```python
import pytest
import asyncio
import time

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling 100 concurrent requests."""
    start_time = time.time()

    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks)

    duration = time.time() - start_time

    assert all(r.success for r in results)
    assert duration < 5.0  # Must complete in < 5 seconds
```

## Test Coverage

### Current Coverage

```
api-gateway/          : 95%
agent-container/      : 92%
dashboard-api/        : 90%
integrations/packages/: 98%
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest tests/ -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Debugging Tests

### Run Single Test

```bash
pytest tests/test_webhook.py::test_github_webhook -v
```

### Run with Debug Output

```bash
pytest tests/ -v -s  # -s shows print statements
```

### Run with PDB on Failure

```bash
pytest tests/ --pdb  # Drop into debugger on failure
```

## Common Issues

### Async Tests Not Running

**Problem**: Async tests are skipped

**Solution**: Install pytest-asyncio and add marker
```python
@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Flaky Tests

**Problem**: Tests pass sometimes, fail others

**Solution**:
- Remove time.sleep()
- Use proper mocks
- Avoid race conditions
- Use deterministic test data

### Slow Tests

**Problem**: Tests take > 5 seconds

**Solution**:
- Mock external calls
- Use in-memory databases
- Run operations in parallel
- Remove unnecessary setup/teardown

## Best Practices

✅ **DO**:
- Use descriptive test names
- Test one thing per test
- Use fixtures for common setup
- Mock external dependencies
- Use async/await correctly
- Write fast tests (< 5s per file)

❌ **DON'T**:
- Use time.sleep()
- Make real API calls
- Share state between tests
- Skip assertions
- Write flaky tests
- Write slow tests

## Example: Complete Test File

```python
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
import respx

from myapp.client import APIClient
from myapp.models import Request, Response
from myapp.exceptions import APIError


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def api_client(mock_http_client):
    return APIClient(http_client=mock_http_client)


class TestAPIClient:
    """Test suite for APIClient."""

    @pytest.mark.asyncio
    async def test_successful_request(self, api_client, mock_http_client):
        """Test successful API request."""
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={"status": "success"})
        )

        result = await api_client.make_request(
            Request(endpoint="/test", data={"key": "value"})
        )

        assert result.status == "success"
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_error(self, api_client, mock_http_client):
        """Test API error handling."""
        mock_http_client.post.side_effect = Exception("Network error")

        with pytest.raises(APIError) as exc_info:
            await api_client.make_request(
                Request(endpoint="/test", data={})
            )

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error(self):
        """Test input validation."""
        with pytest.raises(ValidationError):
            Request(endpoint="", data={})

    @pytest.mark.asyncio
    @respx.mock
    async def test_real_http_mock(self):
        """Test with respx HTTP mocking."""
        respx.post("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        async with AsyncClient() as client:
            response = await client.post("https://api.example.com/test")
            assert response.json() == {"result": "ok"}
```

## Summary

- ✅ All tests MUST pass gracefully
- ✅ Tests MUST run fast (< 5s per file)
- ✅ Use mocks for external dependencies
- ✅ NO flaky tests
- ✅ 100% type coverage
- ✅ Use pytest-asyncio for async
- ✅ Write descriptive test names
- ✅ One assertion per test when possible

**Before committing, run all tests and ensure they pass!**
