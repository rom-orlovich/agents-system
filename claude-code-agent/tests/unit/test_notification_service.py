"""
Tests for unified notification service - written first following TDD approach.

The notification service consolidates send_slack_notification from:
- github/utils.py
- jira/utils.py
- slack/utils.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestNotificationConfig:
    """Tests for notification configuration."""

    def test_default_config(self):
        """Test default notification configuration."""
        from domain.notifications import NotificationConfig

        config = NotificationConfig()

        assert config.enabled is True
        assert config.success_channel == "#ai-agent-activity"
        assert config.error_channel == "#ai-agent-errors"

    def test_config_from_env(self):
        """Test configuration from environment."""
        from domain.notifications import NotificationConfig

        with patch.dict("os.environ", {
            "SLACK_NOTIFICATIONS_ENABLED": "false",
            "SLACK_CHANNEL_AGENTS": "#custom-agents",
            "SLACK_CHANNEL_ERRORS": "#custom-errors",
        }):
            config = NotificationConfig.from_env()

            assert config.enabled is False
            assert config.success_channel == "#custom-agents"
            assert config.error_channel == "#custom-errors"

    def test_get_channel_for_success(self):
        """Test getting channel for successful task."""
        from domain.notifications import NotificationConfig

        config = NotificationConfig(
            success_channel="#success",
            error_channel="#errors",
        )

        assert config.get_channel(success=True) == "#success"

    def test_get_channel_for_failure(self):
        """Test getting channel for failed task."""
        from domain.notifications import NotificationConfig

        config = NotificationConfig(
            success_channel="#success",
            error_channel="#errors",
        )

        assert config.get_channel(success=False) == "#errors"


class TestNotificationBuilder:
    """Tests for notification block building."""

    def test_build_basic_notification_blocks(self):
        """Test building basic notification blocks."""
        from domain.notifications import NotificationBuilder
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        blocks = NotificationBuilder.build_blocks(notification)

        assert len(blocks) > 0
        assert blocks[0]["type"] == "section"

    def test_build_notification_with_result(self):
        """Test building notification with result."""
        from domain.notifications import NotificationBuilder
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
            result="Review completed with 3 suggestions",
        )

        blocks = NotificationBuilder.build_blocks(notification)

        # Should have result block
        block_texts = [str(b) for b in blocks]
        assert any("Result" in t or "Review" in t for t in block_texts)

    def test_build_notification_with_error(self):
        """Test building notification with error."""
        from domain.notifications import NotificationBuilder
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=False,
            error="Rate limit exceeded",
        )

        blocks = NotificationBuilder.build_blocks(notification)

        # Should have error block
        block_texts = [str(b) for b in blocks]
        assert any("Error" in t or "Rate limit" in t for t in block_texts)

    def test_build_approval_buttons(self):
        """Test building approval buttons."""
        from domain.notifications import NotificationBuilder
        from domain.models import RoutingMetadata

        routing = RoutingMetadata(repo="owner/repo", pr_number=123)

        buttons = NotificationBuilder.build_approval_buttons(
            task_id="task-123",
            command="review",
            routing=routing,
            source="github",
        )

        assert len(buttons) > 0
        assert any(b.get("type") == "actions" for b in buttons)


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        client = AsyncMock()
        client.post_message = AsyncMock(return_value={"ok": True, "ts": "123.456"})
        return client

    @pytest.fixture
    def service(self, mock_slack_client):
        """Create notification service with mock client."""
        from domain.notifications import NotificationService, NotificationConfig

        config = NotificationConfig(enabled=True)
        return NotificationService(mock_slack_client, config)

    @pytest.mark.asyncio
    async def test_send_notification_success(self, service, mock_slack_client):
        """Test sending notification for successful task."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        result = await service.send(notification)

        assert result is True
        mock_slack_client.post_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_failure(self, service, mock_slack_client):
        """Test sending notification for failed task."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=False,
            error="Task failed",
        )

        result = await service.send(notification)

        assert result is True
        # Should use error channel
        call_args = mock_slack_client.post_message.call_args
        assert "#ai-agent-errors" in str(call_args)

    @pytest.mark.asyncio
    async def test_send_notification_disabled(self, mock_slack_client):
        """Test that disabled notifications return False."""
        from domain.notifications import NotificationService, NotificationConfig
        from domain.models import TaskNotification, WebhookSource

        config = NotificationConfig(enabled=False)
        service = NotificationService(mock_slack_client, config)

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        result = await service.send(notification)

        assert result is False
        mock_slack_client.post_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_notification_channel_not_found(self, service, mock_slack_client):
        """Test handling channel not found error."""
        from domain.models import TaskNotification, WebhookSource

        mock_slack_client.post_message.side_effect = Exception("channel_not_found")

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        result = await service.send(notification)

        # Should return False but not raise
        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_approval_buttons(self, service, mock_slack_client):
        """Test sending notification with approval buttons."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
            routing={"repo": "owner/repo", "pr_number": 123},
        )

        await service.send(notification, requires_approval=True)

        # Verify blocks were included
        call_args = mock_slack_client.post_message.call_args
        assert "blocks" in call_args.kwargs or len(call_args.args) > 2


class TestTaskSummaryExtractor:
    """Tests for task summary extraction."""

    def test_extract_summary_from_short_result(self):
        """Test extracting summary from short result."""
        from domain.notifications import extract_task_summary

        result = "Review completed. Found 3 issues."

        summary = extract_task_summary(result)

        assert summary.summary is not None
        assert len(summary.summary) > 0

    def test_extract_summary_from_long_result(self):
        """Test extracting summary from long result."""
        from domain.notifications import extract_task_summary

        result = "A" * 1000  # Long result

        summary = extract_task_summary(result)

        # Summary should be truncated
        assert len(summary.summary) < 1000

    def test_extract_summary_with_classification(self):
        """Test extracting summary with classification."""
        from domain.notifications import extract_task_summary

        result = "Task completed"
        metadata = {"classification": "COMPLEX"}

        summary = extract_task_summary(result, metadata)

        assert summary.classification == "COMPLEX"
