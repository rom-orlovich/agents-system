"""Tests for the test factories themselves."""

import pytest
from factories.task_factory import TaskFactory, TaskStatus, InvalidTransitionError
from factories.session_factory import SessionFactory
from factories.conversation_factory import ConversationFactory
from factories.webhook_factory import WebhookFactory, WebhookValidationError


class TestTaskFactory:
    """Tests for TaskFactory."""

    def setup_method(self):
        TaskFactory.reset()

    def test_create_task(self):
        """TaskFactory creates valid tasks."""
        task = TaskFactory.create(input_message="Test task")
        assert task.task_id.startswith("task-")
        assert task.input_message == "Test task"
        assert task.status == TaskStatus.QUEUED

    def test_create_completed_task(self):
        """TaskFactory creates completed tasks."""
        task = TaskFactory.create_completed(cost_usd=0.10)
        assert task.status == TaskStatus.COMPLETED
        assert task.cost_usd == 0.10

    def test_task_transitions(self):
        """Task status transitions work correctly."""
        task = TaskFactory.create()
        assert task.status == TaskStatus.QUEUED

        task.start()
        assert task.status == TaskStatus.RUNNING

        task.complete(result="Done", cost_usd=0.05)
        assert task.status == TaskStatus.COMPLETED

    def test_invalid_transition_raises(self):
        """Invalid transitions raise InvalidTransitionError."""
        task = TaskFactory.create_completed()
        with pytest.raises(InvalidTransitionError):
            task.start()


class TestSessionFactory:
    """Tests for SessionFactory."""

    def setup_method(self):
        SessionFactory.reset()

    def test_create_session(self):
        """SessionFactory creates valid sessions."""
        session = SessionFactory.create(user_id="user-1", machine_id="machine-1")
        assert session.session_id.startswith("session-")
        assert session.user_id == "user-1"
        assert session.active is True

    def test_session_cost_accumulation(self):
        """Session accumulates task costs."""
        TaskFactory.reset()
        session = SessionFactory.create()
        task = TaskFactory.create_completed(cost_usd=0.10)
        session.add_completed_task(task)
        assert session.total_cost_usd == 0.10
        assert session.total_tasks == 1


class TestConversationFactory:
    """Tests for ConversationFactory."""

    def setup_method(self):
        ConversationFactory.reset()

    def test_create_conversation(self):
        """ConversationFactory creates valid conversations."""
        conv = ConversationFactory.create(title="Test conversation")
        assert conv.conversation_id.startswith("conv-")
        assert conv.title == "Test conversation"

    def test_conversation_with_messages(self):
        """ConversationFactory creates conversations with messages."""
        conv = ConversationFactory.create_with_messages(message_count=3)
        assert len(conv.messages) == 3


class TestWebhookFactory:
    """Tests for WebhookFactory."""

    def setup_method(self):
        WebhookFactory.reset()

    def test_create_webhook(self):
        """WebhookFactory creates valid webhooks."""
        webhook = WebhookFactory.create(name="Test Webhook")
        assert webhook.webhook_id.startswith("webhook-")
        assert webhook.name == "Test Webhook"

    def test_webhook_validation(self):
        """Webhook validation catches errors."""
        webhook = WebhookFactory.create(endpoint="/invalid")
        with pytest.raises(WebhookValidationError):
            webhook.validate()

    def test_github_webhook(self):
        """GitHub webhook factory creates valid webhook."""
        webhook = WebhookFactory.create_github_webhook()
        assert webhook.provider == "github"
        assert webhook.is_builtin is True
        webhook.validate()
