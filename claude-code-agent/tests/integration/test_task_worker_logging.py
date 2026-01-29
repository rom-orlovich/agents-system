"""Integration tests for task worker logging (TDD RED phase).

Tests verify that TaskLogger correctly captures agent output and execution
metrics from the task worker.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from workers.task_worker import TaskWorker
from core.task_logger import TaskLogger
from core.database.models import TaskDB
from shared import TaskStatus, AgentType
from core.websocket_hub import WebSocketHub


@pytest.mark.integration
class TestTaskWorkerLogging:
    """Test task worker logging integration."""

    async def test_task_worker_creates_log_directory(self, db, tmp_path):
        """Test: Task worker creates log directory for task."""
        # Create task
        task = TaskDB(
            task_id="task-worker-log-001",
            session_id="session-001",
            user_id="user-001",
            assigned_agent="brain",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message="Test task",
            source="webhook",
            source_metadata='{"provider": "github"}'
        )
        db.add(task)
        await db.commit()

        # Mock Claude CLI execution
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Task completed"
        mock_result.cost_usd = 0.05
        mock_result.input_tokens = 100
        mock_result.output_tokens = 50

        with patch("workers.task_worker.run_claude_cli", return_value=(mock_result, None)), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-001")

        # Verify log directory was created
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1, "Expected task log directory to be created"

    async def test_task_worker_writes_metadata(self, db, tmp_path):
        """Test: Task worker writes metadata.json with task info."""
        task = TaskDB(
            task_id="task-worker-log-002",
            session_id="session-002",
            user_id="user-002",
            assigned_agent="planning",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message="Test metadata",
            source="webhook",
            source_metadata='{"provider": "jira"}'
        )
        db.add(task)
        await db.commit()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Done"
        mock_result.cost_usd = 0.02
        mock_result.input_tokens = 50
        mock_result.output_tokens = 25

        with patch("workers.task_worker.run_claude_cli", return_value=(mock_result, None)), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-002")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check metadata file
        metadata_file = task_dirs[0] / "metadata.json"
        assert metadata_file.exists(), "metadata.json should be created"

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["task_id"] == "task-worker-log-002"
        assert metadata["assigned_agent"] == "planning"
        assert "started_at" in metadata

    async def test_task_worker_logs_agent_output(self, db, tmp_path):
        """Test: Task worker captures agent output in JSONL format."""
        task = TaskDB(
            task_id="task-worker-log-003",
            session_id="session-003",
            user_id="user-003",
            assigned_agent="executor",
            agent_type=AgentType.EXECUTOR,
            status=TaskStatus.QUEUED,
            input_message="Test output logging",
            source="dashboard"
        )
        db.add(task)
        await db.commit()

        # Mock streaming output
        async def mock_cli(*args, **kwargs):
            output_queue = kwargs.get("output_queue")
            if output_queue:
                await output_queue.put("[SYSTEM] Starting...\n")
                await output_queue.put("Agent is thinking\n")
                await output_queue.put("Using Read tool\n")
                await output_queue.put(None)  # End stream

            result = MagicMock()
            result.success = True
            result.output = "Completed"
            result.cost_usd = 0.03
            result.input_tokens = 75
            result.output_tokens = 40
            return result, None

        with patch("workers.task_worker.run_claude_cli", side_effect=mock_cli), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-003")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check agent output file
        output_file = task_dirs[0] / "03-agent-output.jsonl"
        assert output_file.exists(), "03-agent-output.jsonl should be created"

        # Verify JSONL format
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) >= 1, "At least one output line should be logged"

        # Parse first line
        first_output = json.loads(lines[0])
        assert "timestamp" in first_output
        assert "content" in first_output or "message" in first_output

    async def test_task_worker_writes_final_result(self, db, tmp_path):
        """Test: Task worker writes final result with metrics."""
        task = TaskDB(
            task_id="task-worker-log-004",
            session_id="session-004",
            user_id="user-004",
            assigned_agent="brain",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message="Test final result",
            source="webhook"
        )
        db.add(task)
        await db.commit()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Task completed successfully"
        mock_result.cost_usd = 0.12
        mock_result.input_tokens = 500
        mock_result.output_tokens = 300

        with patch("workers.task_worker.run_claude_cli", return_value=(mock_result, None)), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-004")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check final result file
        result_file = task_dirs[0] / "04-final-result.json"
        assert result_file.exists(), "04-final-result.json should be created"

        with open(result_file) as f:
            result_data = json.load(f)

        assert result_data["success"] is True
        assert "result" in result_data
        assert "metrics" in result_data
        assert result_data["metrics"]["cost_usd"] == 0.12
        assert result_data["metrics"]["input_tokens"] == 500
        assert result_data["metrics"]["output_tokens"] == 300

    async def test_task_worker_logs_failure(self, db, tmp_path):
        """Test: Task worker logs task failure correctly."""
        task = TaskDB(
            task_id="task-worker-log-005",
            session_id="session-005",
            user_id="user-005",
            assigned_agent="executor",
            agent_type=AgentType.EXECUTOR,
            status=TaskStatus.QUEUED,
            input_message="Test failure",
            source="dashboard"
        )
        db.add(task)
        await db.commit()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = None
        mock_result.error = "Task timeout"
        mock_result.cost_usd = 0.0
        mock_result.input_tokens = 0
        mock_result.output_tokens = 0

        with patch("workers.task_worker.run_claude_cli", return_value=(mock_result, None)), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-005")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check final result file
        result_file = task_dirs[0] / "04-final-result.json"
        assert result_file.exists(), "04-final-result.json should be created even on failure"

        with open(result_file) as f:
            result_data = json.load(f)

        assert result_data["success"] is False
        assert "error" in result_data
        assert result_data["error"] == "Task timeout"

    async def test_task_worker_logs_streaming_output(self, db, tmp_path):
        """Test: Task worker logs streaming output in real-time."""
        task = TaskDB(
            task_id="task-worker-log-006",
            session_id="session-006",
            user_id="user-006",
            assigned_agent="planning",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message="Test streaming",
            source="webhook"
        )
        db.add(task)
        await db.commit()

        # Mock streaming with multiple chunks
        async def mock_cli_streaming(*args, **kwargs):
            output_queue = kwargs.get("output_queue")
            if output_queue:
                chunks = [
                    "Starting analysis...\n",
                    "Reading file...\n",
                    "Processing data...\n",
                    "Generating response...\n",
                    "Complete.\n"
                ]
                for chunk in chunks:
                    await output_queue.put(chunk)
                await output_queue.put(None)

            result = MagicMock()
            result.success = True
            result.output = "Analysis complete"
            result.cost_usd = 0.08
            result.input_tokens = 200
            result.output_tokens = 150
            return result, None

        with patch("workers.task_worker.run_claude_cli", side_effect=mock_cli_streaming), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-006")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check that multiple output lines were captured
        output_file = task_dirs[0] / "03-agent-output.jsonl"
        if output_file.exists():
            lines = output_file.read_text().strip().split("\n")
            # Should have multiple output entries
            assert len(lines) >= 3, "Multiple streaming outputs should be logged"

    async def test_task_worker_logs_duration_metrics(self, db, tmp_path):
        """Test: Task worker logs execution duration in final result."""
        task = TaskDB(
            task_id="task-worker-log-007",
            session_id="session-007",
            user_id="user-007",
            assigned_agent="executor",
            agent_type=AgentType.EXECUTOR,
            status=TaskStatus.QUEUED,
            input_message="Test duration",
            source="dashboard"
        )
        db.add(task)
        await db.commit()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Done"
        mock_result.cost_usd = 0.04
        mock_result.input_tokens = 100
        mock_result.output_tokens = 60

        with patch("workers.task_worker.run_claude_cli", return_value=(mock_result, None)), \
             patch("core.config.settings.task_logs_enabled", True), \
             patch("core.config.settings.task_logs_dir", tmp_path), \
             patch("workers.task_worker.settings.task_logs_enabled", True), \
             patch("workers.task_worker.settings.task_logs_dir", tmp_path):

            ws_hub = WebSocketHub()
            worker = TaskWorker(ws_hub)
            await worker._process_task("task-worker-log-007")

        # Find task directory
        task_dirs = list(tmp_path.glob("task-worker-log-*"))
        assert len(task_dirs) >= 1

        # Check final result has duration
        result_file = task_dirs[0] / "04-final-result.json"
        if result_file.exists():
            with open(result_file) as f:
                result_data = json.load(f)

            assert "metrics" in result_data
            # Duration should be present (might be 0 in fast tests)
            assert "duration_seconds" in result_data["metrics"]
