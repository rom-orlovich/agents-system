"""Unit tests for TaskLogger class (TDD RED phase)."""

import pytest
import json
from datetime import datetime, timezone
from core.task_logger import TaskLogger


class TestTaskLoggerInit:
    """Test TaskLogger initialization."""

    def test_task_logger_creates_directory(self, tmp_path):
        """Test: TaskLogger creates task directory on initialization."""
        logger = TaskLogger("task-001", tmp_path)

        assert logger.get_log_dir().exists()
        assert logger.get_log_dir().is_dir()
        assert logger.get_log_dir().name == "task-001"

    def test_task_logger_uses_existing_directory(self, tmp_path):
        """Test: TaskLogger works with existing directory."""
        task_dir = tmp_path / "task-002"
        task_dir.mkdir()

        logger = TaskLogger("task-002", tmp_path)

        assert logger.get_log_dir() == task_dir
        assert logger.get_log_dir().exists()

    def test_task_logger_stores_task_id(self, tmp_path):
        """Test: TaskLogger stores task_id correctly."""
        logger = TaskLogger("task-003", tmp_path)

        assert logger.task_id == "task-003"

    def test_task_logger_stores_base_dir(self, tmp_path):
        """Test: TaskLogger stores logs_base_dir correctly."""
        logger = TaskLogger("task-004", tmp_path)

        assert logger.logs_base_dir == tmp_path


class TestTaskLoggerWriteMetadata:
    """Test TaskLogger.write_metadata()."""

    def test_write_metadata_creates_file(self, tmp_path):
        """Test: write_metadata creates metadata.json file."""
        logger = TaskLogger("task-100", tmp_path)

        metadata = {
            "task_id": "task-100",
            "source": "webhook",
            "provider": "github",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "queued"
        }

        logger.write_metadata(metadata)

        metadata_file = logger.get_log_dir() / "metadata.json"
        assert metadata_file.exists()

    def test_write_metadata_contains_correct_data(self, tmp_path):
        """Test: metadata.json contains correct data."""
        logger = TaskLogger("task-101", tmp_path)

        metadata = {
            "task_id": "task-101",
            "source": "webhook",
            "provider": "jira",
            "status": "running"
        }

        logger.write_metadata(metadata)

        metadata_file = logger.get_log_dir() / "metadata.json"
        with open(metadata_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data == metadata
        assert saved_data["task_id"] == "task-101"
        assert saved_data["provider"] == "jira"

    def test_write_metadata_overwrites_existing(self, tmp_path):
        """Test: write_metadata overwrites existing metadata.json."""
        logger = TaskLogger("task-102", tmp_path)

        metadata1 = {"status": "queued"}
        metadata2 = {"status": "running"}

        logger.write_metadata(metadata1)
        logger.write_metadata(metadata2)

        metadata_file = logger.get_log_dir() / "metadata.json"
        with open(metadata_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data["status"] == "running"


class TestTaskLoggerWriteInput:
    """Test TaskLogger.write_input()."""

    def test_write_input_creates_file(self, tmp_path):
        """Test: write_input creates 01-input.json file."""
        logger = TaskLogger("task-200", tmp_path)

        input_data = {
            "message": "Fix the authentication bug",
            "source_metadata": {
                "webhook_id": "wh-123",
                "event_type": "issue_comment"
            }
        }

        logger.write_input(input_data)

        input_file = logger.get_log_dir() / "01-input.json"
        assert input_file.exists()

    def test_write_input_contains_correct_data(self, tmp_path):
        """Test: 01-input.json contains correct data."""
        logger = TaskLogger("task-201", tmp_path)

        input_data = {
            "message": "Review this PR",
            "source_metadata": {
                "pr_number": 42,
                "repository": "test/repo"
            }
        }

        logger.write_input(input_data)

        input_file = logger.get_log_dir() / "01-input.json"
        with open(input_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data == input_data
        assert saved_data["message"] == "Review this PR"
        assert saved_data["source_metadata"]["pr_number"] == 42


class TestTaskLoggerAppendWebhookEvent:
    """Test TaskLogger.append_webhook_event()."""

    def test_append_webhook_event_creates_file(self, tmp_path):
        """Test: append_webhook_event creates 02-webhook-flow.jsonl file."""
        logger = TaskLogger("task-300", tmp_path)

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "received",
            "event_type": "pull_request"
        }

        logger.append_webhook_event(event)

        webhook_file = logger.get_log_dir() / "02-webhook-flow.jsonl"
        assert webhook_file.exists()

    def test_append_webhook_event_jsonl_format(self, tmp_path):
        """Test: webhook events are stored in JSONL format (one JSON per line)."""
        logger = TaskLogger("task-301", tmp_path)

        event1 = {"timestamp": "2024-01-01T00:00:00Z", "stage": "received"}
        event2 = {"timestamp": "2024-01-01T00:00:01Z", "stage": "validated"}

        logger.append_webhook_event(event1)
        logger.append_webhook_event(event2)

        webhook_file = logger.get_log_dir() / "02-webhook-flow.jsonl"
        lines = webhook_file.read_text().strip().split("\n")

        assert len(lines) == 2
        assert json.loads(lines[0]) == event1
        assert json.loads(lines[1]) == event2

    def test_append_webhook_event_multiple_appends(self, tmp_path):
        """Test: Multiple appends preserve previous events."""
        logger = TaskLogger("task-302", tmp_path)

        events = [
            {"stage": "received"},
            {"stage": "validation"},
            {"stage": "task_created"},
            {"stage": "response_sent"}
        ]

        for event in events:
            logger.append_webhook_event(event)

        webhook_file = logger.get_log_dir() / "02-webhook-flow.jsonl"
        lines = webhook_file.read_text().strip().split("\n")

        assert len(lines) == 4
        for i, line in enumerate(lines):
            assert json.loads(line)["stage"] == events[i]["stage"]


class TestTaskLoggerAppendAgentOutput:
    """Test TaskLogger.append_agent_output()."""

    def test_append_agent_output_creates_file(self, tmp_path):
        """Test: append_agent_output creates 03-agent-output.jsonl file."""
        logger = TaskLogger("task-400", tmp_path)

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "thinking",
            "content": "I need to analyze the code first"
        }

        logger.append_agent_output(output)

        output_file = logger.get_log_dir() / "03-agent-output.jsonl"
        assert output_file.exists()

    def test_append_agent_output_jsonl_format(self, tmp_path):
        """Test: agent outputs are stored in JSONL format."""
        logger = TaskLogger("task-401", tmp_path)

        output1 = {"type": "thinking", "content": "First thought"}
        output2 = {"type": "tool_call", "tool": "Read", "params": {"file": "test.py"}}
        output3 = {"type": "tool_result", "tool": "Read", "success": True}

        logger.append_agent_output(output1)
        logger.append_agent_output(output2)
        logger.append_agent_output(output3)

        output_file = logger.get_log_dir() / "03-agent-output.jsonl"
        lines = output_file.read_text().strip().split("\n")

        assert len(lines) == 3
        assert json.loads(lines[0])["type"] == "thinking"
        assert json.loads(lines[1])["type"] == "tool_call"
        assert json.loads(lines[2])["type"] == "tool_result"

    def test_append_agent_output_streaming_scenario(self, tmp_path):
        """Test: Streaming scenario - multiple outputs appended over time."""
        logger = TaskLogger("task-402", tmp_path)

        # Simulate streaming agent output
        outputs = [
            {"type": "system", "message": "Task started"},
            {"type": "thinking", "content": "Let me read the file"},
            {"type": "tool_call", "tool": "Read"},
            {"type": "tool_result", "tool": "Read", "lines": 150},
            {"type": "message", "content": "Here's my analysis"},
        ]

        for output in outputs:
            logger.append_agent_output(output)

        output_file = logger.get_log_dir() / "03-agent-output.jsonl"
        lines = output_file.read_text().strip().split("\n")

        assert len(lines) == 5
        assert json.loads(lines[0])["type"] == "system"
        assert json.loads(lines[4])["type"] == "message"


class TestTaskLoggerWriteFinalResult:
    """Test TaskLogger.write_final_result()."""

    def test_write_final_result_creates_file(self, tmp_path):
        """Test: write_final_result creates 04-final-result.json file."""
        logger = TaskLogger("task-500", tmp_path)

        result = {
            "success": True,
            "result": "Task completed successfully",
            "metrics": {
                "cost_usd": 0.0234,
                "input_tokens": 1500,
                "output_tokens": 800
            }
        }

        logger.write_final_result(result)

        result_file = logger.get_log_dir() / "04-final-result.json"
        assert result_file.exists()

    def test_write_final_result_contains_correct_data(self, tmp_path):
        """Test: 04-final-result.json contains correct data."""
        logger = TaskLogger("task-501", tmp_path)

        result = {
            "success": False,
            "result": None,
            "error": "Task failed due to timeout",
            "metrics": {
                "cost_usd": 0.0,
                "duration_seconds": 3600
            }
        }

        logger.write_final_result(result)

        result_file = logger.get_log_dir() / "04-final-result.json"
        with open(result_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data == result
        assert saved_data["success"] is False
        assert saved_data["error"] == "Task failed due to timeout"


class TestTaskLoggerErrorHandling:
    """Test TaskLogger error handling."""

    def test_write_to_readonly_directory(self, tmp_path):
        """Test: TaskLogger handles read-only directory gracefully."""
        logger = TaskLogger("task-600", tmp_path)

        # Make directory read-only
        import os
        os.chmod(logger.get_log_dir(), 0o444)

        # Should not raise exception, but handle error gracefully
        # Implementation should log error but not crash
        try:
            logger.write_metadata({"test": "data"})
        except PermissionError:
            # Expected behavior - we want to catch this in implementation
            pass
        finally:
            # Restore permissions for cleanup
            os.chmod(logger.get_log_dir(), 0o755)

    def test_write_invalid_json(self, tmp_path):
        """Test: TaskLogger handles invalid JSON data."""
        logger = TaskLogger("task-601", tmp_path)

        # Non-serializable object
        class CustomObject:
            pass

        invalid_data = {"obj": CustomObject()}

        # Should handle TypeError gracefully
        with pytest.raises(TypeError):
            logger.write_metadata(invalid_data)

    def test_append_to_corrupted_jsonl(self, tmp_path):
        """Test: TaskLogger handles corrupted JSONL file."""
        logger = TaskLogger("task-602", tmp_path)

        # Write valid event first
        logger.append_webhook_event({"stage": "received"})

        # Corrupt the file
        webhook_file = logger.get_log_dir() / "02-webhook-flow.jsonl"
        with open(webhook_file, "a") as f:
            f.write("THIS IS NOT JSON\n")

        # Should still be able to append new events
        logger.append_webhook_event({"stage": "validated"})

        # File should contain the corrupted line and new valid line
        lines = webhook_file.read_text().strip().split("\n")
        assert len(lines) == 3


class TestTaskLoggerIntegration:
    """Integration tests for TaskLogger - testing complete flows."""

    def test_complete_task_logging_flow(self, tmp_path):
        """Test: Complete task logging flow creates all expected files."""
        logger = TaskLogger("task-999", tmp_path)

        # 1. Write metadata
        logger.write_metadata({
            "task_id": "task-999",
            "source": "webhook",
            "provider": "github",
            "status": "running"
        })

        # 2. Write input
        logger.write_input({
            "message": "Fix bug in auth module",
            "source_metadata": {"pr_number": 123}
        })

        # 3. Append webhook events
        logger.append_webhook_event({"stage": "received"})
        logger.append_webhook_event({"stage": "validated"})
        logger.append_webhook_event({"stage": "task_created"})

        # 4. Append agent outputs
        logger.append_agent_output({"type": "thinking", "content": "Analyzing..."})
        logger.append_agent_output({"type": "tool_call", "tool": "Read"})
        logger.append_agent_output({"type": "message", "content": "Found the bug"})

        # 5. Write final result
        logger.write_final_result({
            "success": True,
            "result": "Bug fixed",
            "metrics": {"cost_usd": 0.05}
        })

        # Verify all files exist
        task_dir = logger.get_log_dir()
        assert (task_dir / "metadata.json").exists()
        assert (task_dir / "01-input.json").exists()
        assert (task_dir / "02-webhook-flow.jsonl").exists()
        assert (task_dir / "03-agent-output.jsonl").exists()
        assert (task_dir / "04-final-result.json").exists()

        # Verify file contents
        with open(task_dir / "metadata.json") as f:
            metadata = json.load(f)
            assert metadata["task_id"] == "task-999"

        webhook_lines = (task_dir / "02-webhook-flow.jsonl").read_text().strip().split("\n")
        assert len(webhook_lines) == 3

        agent_lines = (task_dir / "03-agent-output.jsonl").read_text().strip().split("\n")
        assert len(agent_lines) == 3
