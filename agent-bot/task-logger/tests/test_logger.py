import json
from pathlib import Path

import pytest

from logger import TaskLogger


def test_create_task_directory(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    assert logger.log_dir.exists()
    assert logger.log_dir == tmp_path / "test-001"


def test_write_metadata(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    metadata = {"task_id": "test-001", "source": "webhook"}
    logger.write_metadata(metadata)

    metadata_file = tmp_path / "test-001" / "metadata.json"
    assert metadata_file.exists()

    with open(metadata_file, "r") as f:
        loaded = json.load(f)
        assert loaded == metadata


def test_write_input(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    input_data = {"message": "Fix the bug"}
    logger.write_input(input_data)

    input_file = tmp_path / "test-001" / "01-input.json"
    assert input_file.exists()

    with open(input_file, "r") as f:
        loaded = json.load(f)
        assert loaded == input_data


def test_append_webhook_event(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    event1 = {"timestamp": "2026-01-31T12:00:00Z", "stage": "received", "data": {}}
    event2 = {"timestamp": "2026-01-31T12:00:01Z", "stage": "validated", "data": {}}

    logger.append_webhook_event(event1)
    logger.append_webhook_event(event2)

    webhook_file = tmp_path / "test-001" / "02-webhook-flow.jsonl"
    assert webhook_file.exists()

    with open(webhook_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == event1
        assert json.loads(lines[1]) == event2


def test_append_agent_output(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    output = {"timestamp": "2026-01-31T12:00:00Z", "type": "output", "content": "test"}

    logger.append_agent_output(output)

    output_file = tmp_path / "test-001" / "03-agent-output.jsonl"
    assert output_file.exists()

    with open(output_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert json.loads(lines[0]) == output


def test_append_user_input(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    user_input = {
        "timestamp": "2026-01-31T12:00:00Z",
        "type": "user_response",
        "question_type": "approval",
        "content": "yes",
    }

    logger.append_user_input(user_input)

    user_input_file = tmp_path / "test-001" / "03-user-inputs.jsonl"
    assert user_input_file.exists()

    with open(user_input_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert json.loads(lines[0]) == user_input


def test_write_final_result(tmp_path):
    logger = TaskLogger("test-001", tmp_path)
    result = {
        "success": True,
        "result": "Task completed",
        "metrics": {"cost_usd": 0.01, "duration_seconds": 120},
        "completed_at": "2026-01-31T12:02:00Z",
    }

    logger.write_final_result(result)

    result_file = tmp_path / "test-001" / "04-final-result.json"
    assert result_file.exists()

    with open(result_file, "r") as f:
        loaded = json.load(f)
        assert loaded == result
