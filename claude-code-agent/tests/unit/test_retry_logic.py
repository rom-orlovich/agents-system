"""
Tests for retry logic with tenacity - written first following TDD approach.

The retry module provides:
- Configurable retry decorators for external service calls
- Circuit breaker functionality
- Retry policies for different error types
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestRetryDecorators:
    """Tests for retry decorators."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry on transient error."""
        from domain.retry import with_retry

        call_count = 0

        @with_retry(max_attempts=3)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """Test no retry when function succeeds."""
        from domain.retry import with_retry

        call_count = 0

        @with_retry(max_attempts=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test exception raised when max attempts exceeded."""
        from domain.retry import with_retry

        call_count = 0

        @with_retry(max_attempts=3)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_transient_error(self):
        """Test no retry on non-transient errors."""
        from domain.retry import with_retry

        call_count = 0

        @with_retry(max_attempts=3, retry_on=(ConnectionError,))
        async def validation_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            await validation_error()

        assert call_count == 1  # No retry for ValueError


class TestRetryPolicies:
    """Tests for retry policies."""

    def test_default_policy(self):
        """Test default retry policy."""
        from domain.retry import RetryPolicy

        policy = RetryPolicy.default()

        assert policy.max_attempts == 3
        assert policy.wait_min == 2
        assert policy.wait_max == 10

    def test_aggressive_policy(self):
        """Test aggressive retry policy."""
        from domain.retry import RetryPolicy

        policy = RetryPolicy.aggressive()

        assert policy.max_attempts == 5
        assert policy.wait_min == 1

    def test_conservative_policy(self):
        """Test conservative retry policy."""
        from domain.retry import RetryPolicy

        policy = RetryPolicy.conservative()

        assert policy.max_attempts == 2
        assert policy.wait_max >= 30

    def test_no_retry_policy(self):
        """Test no-retry policy."""
        from domain.retry import RetryPolicy

        policy = RetryPolicy.no_retry()

        assert policy.max_attempts == 1


class TestExternalServiceRetry:
    """Tests for external service retry wrappers."""

    @pytest.mark.asyncio
    async def test_github_api_retry(self):
        """Test GitHub API call with retry."""
        from domain.retry import github_api_call

        call_count = 0
        mock_client = AsyncMock()

        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("GitHub API error")
            return {"status": "ok"}

        mock_client.call = flaky_call

        result = await github_api_call(mock_client.call)

        assert result == {"status": "ok"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_jira_api_retry(self):
        """Test Jira API call with retry."""
        from domain.retry import jira_api_call

        call_count = 0

        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Jira API error")
            return {"status": "ok"}

        result = await jira_api_call(flaky_call)

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_slack_api_retry(self):
        """Test Slack API call with retry."""
        from domain.retry import slack_api_call

        call_count = 0

        async def flaky_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Slack API error")
            return {"ok": True}

        result = await slack_api_call(flaky_call)

        assert result == {"ok": True}


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Test retry on rate limit error."""
        from domain.retry import with_retry
        from domain.exceptions import RateLimitError

        call_count = 0

        @with_retry(max_attempts=3, retry_on=(RateLimitError,))
        async def rate_limited_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("github", retry_after=1)
            return "success"

        result = await rate_limited_call()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_respects_retry_after(self):
        """Test that rate limit retry respects retry-after."""
        from domain.retry import with_rate_limit_handling
        from domain.exceptions import RateLimitError
        import time

        call_count = 0
        start_time = time.time()

        @with_rate_limit_handling
        async def rate_limited_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("github", retry_after=1)
            return "success"

        result = await rate_limited_call()
        elapsed = time.time() - start_time

        assert result == "success"
        # Should have waited at least 1 second (with some tolerance)
        assert elapsed >= 0.9
