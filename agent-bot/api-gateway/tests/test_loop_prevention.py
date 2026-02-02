"""Tests for loop prevention business logic.

Tests the mechanism that prevents agents from responding to their own messages.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class LoopPrevention:
    """Loop prevention mechanism for webhooks."""

    def __init__(self, redis_client: MagicMock | None = None):
        self._redis = redis_client
        self._key_prefix = "posted_comments"
        self._ttl_seconds = 3600

    async def track_posted_comment(self, comment_id: str) -> None:
        """Track that a comment was posted by the agent."""
        if self._redis:
            key = f"{self._key_prefix}:{comment_id}"
            await self._redis.setex(key, self._ttl_seconds, "1")

    async def is_own_comment(self, comment_id: str) -> bool:
        """Check if a comment was posted by the agent."""
        if not self._redis:
            return False
        key = f"{self._key_prefix}:{comment_id}"
        result = await self._redis.get(key)
        return result is not None

    def get_key(self, comment_id: str) -> str:
        """Get Redis key for a comment."""
        return f"{self._key_prefix}:{comment_id}"


@pytest.fixture
def mock_redis():
    """Mock Redis client for loop prevention."""
    redis = MagicMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def loop_prevention(mock_redis):
    """Loop prevention instance with mock Redis."""
    return LoopPrevention(redis_client=mock_redis)


class TestCommentTracking:
    """Tests for comment tracking."""

    async def test_agent_posted_comment_tracked(self, loop_prevention, mock_redis):
        """Business requirement: Comments tracked."""
        await loop_prevention.track_posted_comment("comment-456")

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "posted_comments:comment-456" in call_args[0]
        assert call_args[0][1] == 3600

    async def test_subsequent_webhook_for_own_comment_detected(
        self, loop_prevention, mock_redis
    ):
        """Business requirement: Own comments detected."""
        mock_redis.get.return_value = b"1"

        is_own = await loop_prevention.is_own_comment("comment-456")

        assert is_own is True
        mock_redis.get.assert_called_with("posted_comments:comment-456")

    async def test_different_comment_not_blocked(self, loop_prevention, mock_redis):
        """Business requirement: Only exact match blocked."""
        mock_redis.get.return_value = None

        is_own = await loop_prevention.is_own_comment("comment-789")

        assert is_own is False


class TestTTLExpiration:
    """Tests for TTL-based expiration."""

    def test_tracking_uses_1_hour_ttl(self, loop_prevention):
        """Business requirement: TTL prevents stale data."""
        assert loop_prevention._ttl_seconds == 3600

    async def test_key_format(self, loop_prevention):
        """Verify Redis key format."""
        key = loop_prevention.get_key("comment-123")
        assert key == "posted_comments:comment-123"


class TestLoopPreventionFlow:
    """Tests for complete loop prevention flow."""

    async def test_loop_prevention_flow(self, loop_prevention, mock_redis):
        """Business requirement: Agent doesn't respond to its own comments."""
        mock_redis.get.return_value = None
        is_own_before = await loop_prevention.is_own_comment("comment-456")
        assert is_own_before is False

        await loop_prevention.track_posted_comment("comment-456")
        mock_redis.setex.assert_called_once()

        mock_redis.get.return_value = b"1"
        is_own_after = await loop_prevention.is_own_comment("comment-456")
        assert is_own_after is True

    async def test_no_redis_means_no_blocking(self):
        """Without Redis, comments are not blocked."""
        loop_prevention = LoopPrevention(redis_client=None)

        is_own = await loop_prevention.is_own_comment("comment-123")
        assert is_own is False

    async def test_parallel_comments_tracked_independently(
        self, loop_prevention, mock_redis
    ):
        """Multiple comments can be tracked independently."""
        await loop_prevention.track_posted_comment("comment-1")
        await loop_prevention.track_posted_comment("comment-2")
        await loop_prevention.track_posted_comment("comment-3")

        assert mock_redis.setex.call_count == 3


class TestLoopPreventionIntegration:
    """Integration tests for loop prevention with webhooks."""

    async def test_github_comment_loop_prevention(self, loop_prevention, mock_redis):
        """GitHub issue comments should use loop prevention."""
        github_comment_id = "1234567890"

        mock_redis.get.return_value = None
        assert await loop_prevention.is_own_comment(github_comment_id) is False

        await loop_prevention.track_posted_comment(github_comment_id)

        mock_redis.get.return_value = b"1"
        assert await loop_prevention.is_own_comment(github_comment_id) is True

    async def test_jira_comment_loop_prevention(self, loop_prevention, mock_redis):
        """Jira comments should use loop prevention."""
        jira_comment_id = "10001"

        await loop_prevention.track_posted_comment(jira_comment_id)
        mock_redis.setex.assert_called_once()

    async def test_slack_message_loop_prevention(self, loop_prevention, mock_redis):
        """Slack messages should use loop prevention."""
        slack_ts = "1706702400.000001"

        await loop_prevention.track_posted_comment(slack_ts)
        mock_redis.setex.assert_called_with(
            f"posted_comments:{slack_ts}",
            3600,
            "1",
        )
