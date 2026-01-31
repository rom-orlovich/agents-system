"""Tests for conversation business logic.

Tests conversation tracking and metric aggregation.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))


class TestConversationMetricsAggregation:
    """Tests for conversation metrics aggregation."""

    def test_conversation_aggregates_task_metrics(
        self, conversation_factory, task_factory
    ):
        """Business requirement: Roll-up metrics."""
        conversation = conversation_factory.create(title="Fix auth bug")

        task1 = task_factory.create_completed(cost_usd=0.10)
        task1.duration_seconds = 30
        conversation.add_task(task1)

        task2 = task_factory.create_completed(cost_usd=0.25)
        task2.duration_seconds = 60
        conversation.add_task(task2)

        assert conversation.total_cost_usd == 0.35
        assert conversation.total_tasks == 2
        assert conversation.total_duration_seconds == 90

    def test_conversation_started_at_is_earliest_task(
        self, conversation_factory, task_factory
    ):
        """Business requirement: Timeline accuracy."""
        conversation = conversation_factory.create()

        early_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        late_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        task1 = task_factory.create()
        task1.started_at = late_time
        task1.completed_at = late_time + timedelta(minutes=30)
        conversation.add_task(task1)

        task2 = task_factory.create()
        task2.started_at = early_time
        task2.completed_at = early_time + timedelta(minutes=30)
        conversation.add_task(task2)

        assert conversation.started_at == early_time

    def test_conversation_completed_at_is_latest_task(
        self, conversation_factory, task_factory
    ):
        """Business requirement: Timeline accuracy."""
        conversation = conversation_factory.create()

        early_completion = datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        late_completion = datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)

        task1 = task_factory.create()
        task1.started_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        task1.completed_at = early_completion
        conversation.add_task(task1)

        task2 = task_factory.create()
        task2.started_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        task2.completed_at = late_completion
        conversation.add_task(task2)

        assert conversation.completed_at == late_completion


class TestConversationMessages:
    """Tests for conversation message management."""

    def test_messages_ordered_chronologically(self, conversation_factory):
        """Business requirement: Readable history."""
        conversation = conversation_factory.create_with_messages(message_count=5)

        messages = conversation.get_messages_ordered()

        for i in range(1, len(messages)):
            assert messages[i - 1].created_at <= messages[i].created_at

    def test_add_message_updates_conversation(self, conversation_factory):
        """Adding messages updates conversation timestamp."""
        conversation = conversation_factory.create()
        initial_updated = conversation.updated_at

        conversation.add_message(
            message_id="msg-001",
            role="user",
            content="Please help me fix this bug",
        )

        assert len(conversation.messages) == 1
        assert conversation.updated_at >= initial_updated


class TestConversationArchiving:
    """Tests for conversation archiving."""

    def test_archived_conversation_flag(self, conversation_factory):
        """Business requirement: Archive behavior."""
        conversation = conversation_factory.create()
        assert conversation.is_archived is False

        conversation.archive()
        assert conversation.is_archived is True

    def test_archived_conversation_preserves_data(
        self, conversation_factory, task_factory
    ):
        """Archived conversations keep their data."""
        conversation = conversation_factory.create()

        task = task_factory.create_completed(cost_usd=0.50)
        conversation.add_task(task)

        conversation.archive()

        assert conversation.is_archived is True
        assert conversation.total_cost_usd == 0.50
        assert conversation.total_tasks == 1


class TestConversationCreation:
    """Tests for conversation creation."""

    def test_conversation_has_unique_id(self, conversation_factory):
        """Each conversation has unique identifier."""
        conv1 = conversation_factory.create()
        conv2 = conversation_factory.create()

        assert conv1.conversation_id != conv2.conversation_id

    def test_conversation_requires_user_and_title(self, conversation_factory):
        """Conversations need user_id and title."""
        conversation = conversation_factory.create(
            user_id="user-123",
            title="Debug session",
        )

        assert conversation.user_id == "user-123"
        assert conversation.title == "Debug session"


class TestTaskCompletionUpdatesConversation:
    """Tests for task completion updating conversation."""

    def test_task_completion_updates_conversation(
        self, conversation_factory, task_factory
    ):
        """Business requirement: Real-time metrics."""
        conversation = conversation_factory.create()

        assert conversation.total_tasks == 0
        assert conversation.total_cost_usd == 0.0

        task = task_factory.create()
        task.start()
        task.complete(cost_usd=0.15)
        task.duration_seconds = 45

        conversation.add_task(task)

        assert conversation.total_tasks == 1
        assert conversation.total_cost_usd == 0.15
        assert conversation.total_duration_seconds == 45

    def test_failed_task_updates_metrics(self, conversation_factory, task_factory):
        """Failed tasks still count in metrics."""
        conversation = conversation_factory.create()

        task = task_factory.create_failed()
        conversation.add_task(task)

        assert conversation.total_tasks == 1
        assert conversation.total_cost_usd == 0.0
