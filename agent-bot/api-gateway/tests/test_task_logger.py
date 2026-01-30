import pytest
from pathlib import Path
import json
import tempfile
import shutil
from core.task_logger import TaskLogger


@pytest.fixture
def temp_logs_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_task_logger_creates_directory(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    log_dir = temp_logs_dir / task_id
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_task_logger_get_or_create_returns_same_instance(temp_logs_dir: Path):
    task_id = "task-123"
    logger1 = TaskLogger.get_or_create(task_id=task_id, logs_base_dir=temp_logs_dir)
    logger2 = TaskLogger.get_or_create(task_id=task_id, logs_base_dir=temp_logs_dir)

    assert logger1 is logger2


def test_task_logger_write_metadata(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    metadata = {
        "task_id": task_id,
        "source": "webhook",
        "provider": "github",
        "status": "queued",
    }
    task_logger.write_metadata(metadata)

    metadata_file = temp_logs_dir / task_id / "metadata.json"
    assert metadata_file.exists()

    with open(metadata_file) as f:
        saved_metadata = json.load(f)
    assert saved_metadata == metadata


def test_task_logger_write_input(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    input_data = {
        "message": "analyze this issue",
        "source_metadata": {"provider": "github", "event_type": "issues"},
    }
    task_logger.write_input(input_data)

    input_file = temp_logs_dir / task_id / "01-input.json"
    assert input_file.exists()

    with open(input_file) as f:
        saved_input = json.load(f)
    assert saved_input == input_data


def test_task_logger_log_webhook_event(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    task_logger.log_webhook_event(stage="received", provider="github")
    task_logger.log_webhook_event(stage="validation", status="passed")

    webhook_flow_file = temp_logs_dir / task_id / "02-webhook-flow.jsonl"
    assert webhook_flow_file.exists()

    with open(webhook_flow_file) as f:
        lines = f.readlines()
    assert len(lines) == 2

    event1 = json.loads(lines[0])
    assert event1["stage"] == "received"
    assert event1["provider"] == "github"
    assert event1["task_id"] == task_id

    event2 = json.loads(lines[1])
    assert event2["stage"] == "validation"
    assert event2["status"] == "passed"


def test_task_logger_log_queue_event(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    task_logger.log_queue_event(stage="queue_push", queue_name="tasks")

    queue_flow_file = temp_logs_dir / task_id / "03-queue-flow.jsonl"
    assert queue_flow_file.exists()

    with open(queue_flow_file) as f:
        event = json.loads(f.read())
    assert event["stage"] == "queue_push"
    assert event["queue_name"] == "tasks"


def test_task_logger_write_final_result(temp_logs_dir: Path):
    task_id = "task-123"
    task_logger = TaskLogger(task_id=task_id, logs_base_dir=temp_logs_dir)

    final_result = {
        "success": True,
        "result": "Task completed",
        "metrics": {"cost_usd": 0.05, "tokens": 1000},
    }
    task_logger.write_final_result(final_result)

    result_file = temp_logs_dir / task_id / "06-final-result.json"
    assert result_file.exists()

    with open(result_file) as f:
        saved_result = json.load(f)
    assert saved_result == final_result
