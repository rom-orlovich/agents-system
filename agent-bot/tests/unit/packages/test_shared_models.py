"""Tests for shared models."""

from datetime import datetime
from uuid import uuid4
import pytest
from pydantic import ValidationError

import sys
sys.path.insert(0, "integrations/packages")

from shared.models import (
    BaseResponse,
    HealthResponse,
    TaskStatus,
    WebhookEvent,
    TaskRequest,
    TaskResult,
)


def test_base_response_creation():
    """Test BaseResponse model creation."""
    response = BaseResponse(success=True, message="Test message")
    assert response.success is True
    assert response.message == "Test message"
    assert response.data is None


def test_health_response_default_timestamp():
    """Test HealthResponse with default timestamp."""
    response = HealthResponse(status="healthy", service="test-service")
    assert response.status == "healthy"
    assert response.service == "test-service"
    assert isinstance(response.timestamp, datetime)


def test_task_status_lifecycle():
    """Test TaskStatus through different states."""
    task = TaskStatus(status="pending")
    assert task.status == "pending"
    assert task.error is None

    task.status = "in_progress"
    assert task.status == "in_progress"

    task.status = "completed"
    task.result = {"output": "success"}
    assert task.status == "completed"
    assert task.result == {"output": "success"}


def test_webhook_event_validation():
    """Test WebhookEvent validation."""
    event = WebhookEvent(
        source="github",
        event_type="push",
        payload={"ref": "refs/heads/main"},
    )
    assert event.source == "github"
    assert event.event_type == "push"
    assert isinstance(event.event_id, type(uuid4()))


def test_task_request_priority():
    """Test TaskRequest with different priorities."""
    task = TaskRequest(task_type="planning", description="Test task")
    assert task.priority == "medium"

    task_high = TaskRequest(
        task_type="execution", description="Urgent task", priority="high"
    )
    assert task_high.priority == "high"


def test_task_result_immutable():
    """Test TaskResult is frozen."""
    result = TaskResult(
        task_id=uuid4(),
        status="completed",
        duration_seconds=1.5,
        output={"result": "done"},
    )

    with pytest.raises(ValidationError):
        result.status = "failed"


def test_invalid_webhook_source():
    """Test invalid webhook source."""
    with pytest.raises(ValidationError):
        WebhookEvent(
            source="invalid",
            event_type="test",
            payload={},
        )


def test_invalid_task_status():
    """Test invalid task status."""
    with pytest.raises(ValidationError):
        TaskStatus(status="invalid_status")
