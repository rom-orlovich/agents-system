"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime

from shared import (
    Task,
    TaskStatus,
    AgentType,
    Session,
    MachineConfig,
    ClaudeCredentials,
    AuthStatus,
    WebhookConfig,
)


class TestTaskModel:
    """Test Task model validation and transitions."""

    def test_task_creation(self, sample_task):
        """Task can be created with valid data."""
        assert sample_task.task_id == "test-001"
        assert sample_task.status == TaskStatus.QUEUED
        assert sample_task.cost_usd == 0.0

    def test_task_status_transitions(self, sample_task):
        """Task status transitions are validated."""
        # Valid transition: QUEUED -> RUNNING
        assert sample_task.can_transition_to(TaskStatus.RUNNING)
        sample_task.transition_to(TaskStatus.RUNNING)
        assert sample_task.status == TaskStatus.RUNNING

        # Valid transition: RUNNING -> COMPLETED
        assert sample_task.can_transition_to(TaskStatus.COMPLETED)
        sample_task.transition_to(TaskStatus.COMPLETED)
        assert sample_task.status == TaskStatus.COMPLETED

        # Invalid transition: COMPLETED -> RUNNING
        assert not sample_task.can_transition_to(TaskStatus.RUNNING)
        with pytest.raises(ValueError):
            sample_task.transition_to(TaskStatus.RUNNING)

    def test_task_timing_auto_update(self):
        """Task timing fields are automatically updated."""
        task = Task(
            task_id="test-002",
            session_id="session-001",
            user_id="user-001",
            input_message="Test task",
            status=TaskStatus.RUNNING,
        )
        assert task.started_at is not None

        task.status = TaskStatus.COMPLETED
        task = task.model_validate(task.model_dump())
        assert task.completed_at is not None


class TestSessionModel:
    """Test Session model."""

    def test_session_creation(self):
        """Session can be created."""
        session = Session(
            session_id="sess-001",
            user_id="user-001",
            machine_id="machine-001",
        )
        assert session.total_tasks == 0
        assert session.total_cost_usd == 0.0

    def test_session_add_task(self):
        """Session can track tasks."""
        session = Session(
            session_id="sess-001",
            user_id="user-001",
            machine_id="machine-001",
        )
        session.add_task("task-001")
        assert session.total_tasks == 1
        assert "task-001" in session.active_task_ids

        # Adding same task twice doesn't duplicate
        session.add_task("task-001")
        assert session.total_tasks == 1

    def test_session_add_cost(self):
        """Session can track costs."""
        session = Session(
            session_id="sess-001",
            user_id="user-001",
            machine_id="machine-001",
        )
        session.add_cost(0.05)
        assert session.total_cost_usd == 0.05

        session.add_cost(0.03)
        assert session.total_cost_usd == 0.08

        # Negative cost raises error
        with pytest.raises(ValueError):
            session.add_cost(-0.01)


class TestMachineConfig:
    """Test MachineConfig model."""

    def test_valid_machine_id(self):
        """Valid machine ID is accepted."""
        config = MachineConfig(machine_id="claude-agent-001")
        assert config.machine_id == "claude-agent-001"

    def test_invalid_machine_id(self):
        """Invalid machine ID is rejected."""
        with pytest.raises(ValueError):
            MachineConfig(machine_id="invalid@id!")


class TestClaudeCredentials:
    """Test ClaudeCredentials model."""

    def test_credentials_status(self):
        """Credentials status is calculated correctly."""
        # Valid credentials
        future_time = int((datetime.utcnow().timestamp() + 7200) * 1000)  # 2 hours from now
        creds = ClaudeCredentials(
            access_token="token123456789",
            refresh_token="refresh123456789",
            expires_at=future_time,
        )
        assert creds.get_status() == AuthStatus.VALID
        assert not creds.is_expired
        assert not creds.needs_refresh

        # Expired credentials
        past_time = int((datetime.utcnow().timestamp() - 3600) * 1000)  # 1 hour ago
        expired_creds = ClaudeCredentials(
            access_token="token123456789",
            refresh_token="refresh123456789",
            expires_at=past_time,
        )
        assert expired_creds.is_expired
        assert expired_creds.get_status() == AuthStatus.EXPIRED


class TestWebhookConfig:
    """Test WebhookConfig model."""

    def test_webhook_creation(self):
        """Webhook can be created with valid data."""
        webhook = WebhookConfig(
            name="github",
            endpoint="/webhooks/github",
            source="github",
            target_agent="planning",
        )
        assert webhook.name == "github"
        assert webhook.source == "github"

    def test_webhook_name_validation(self):
        """Webhook name must be lowercase alphanumeric with hyphens."""
        # Valid name
        webhook = WebhookConfig(
            name="github-webhook",
            endpoint="/webhooks/github",
            target_agent="planning",
        )
        assert webhook.name == "github-webhook"

        # Invalid name (uppercase)
        with pytest.raises(ValueError):
            WebhookConfig(
                name="GitHub",
                endpoint="/webhooks/github",
                target_agent="planning",
            )

        # Invalid name (special chars)
        with pytest.raises(ValueError):
            WebhookConfig(
                name="github@webhook",
                endpoint="/webhooks/github",
                target_agent="planning",
            )
