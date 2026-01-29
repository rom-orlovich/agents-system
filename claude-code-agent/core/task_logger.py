"""Task logging system for structured logging of task execution.

This module provides the TaskLogger class which creates and manages structured
logs for each task. Logs are stored in a dedicated directory per task with:
- metadata.json: Task metadata (static)
- 01-input.json: Task input (static)
- 02-webhook-flow.jsonl: Webhook events stream (if applicable)
- 03-agent-output.jsonl: Agent output stream (thinking, tool calls, messages)
- 04-final-result.json: Final result and metrics (static)

The logger uses JSONL (JSON Lines) format for streaming data to support
efficient appending and future migration to centralized logging systems.

Thread Safety:
- JSON file writes use atomic write operations (temp file + rename)
- JSONL appends use atomic append mode (safe for concurrent writes on POSIX systems)
"""

import json
import os
import tempfile
import structlog
from pathlib import Path
from typing import Any, Dict

logger = structlog.get_logger(__name__)


class TaskLogger:
    """Structured logger for task execution.

    Creates and manages log files for a single task in a dedicated directory.
    Supports both static JSON files and streaming JSONL files.

    Attributes:
        task_id: Unique identifier for the task
        logs_base_dir: Base directory for all task logs
    """

    def __init__(self, task_id: str, logs_base_dir: Path):
        """Initialize TaskLogger for a specific task.

        Args:
            task_id: Unique identifier for the task
            logs_base_dir: Base directory where task logs will be stored

        The logger will create a subdirectory named {task_id} under logs_base_dir.
        """
        self.task_id = task_id
        self.logs_base_dir = Path(logs_base_dir)
        self._log_dir = self.logs_base_dir / task_id

        # Create task directory if it doesn't exist
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("task_logger_initialized", task_id=task_id, log_dir=str(self._log_dir))
        except Exception as e:
            logger.error("task_logger_init_failed", task_id=task_id, error=str(e))
            raise

    def get_log_dir(self) -> Path:
        """Get the log directory path for this task.

        Returns:
            Path to the task's log directory
        """
        return self._log_dir

    def write_metadata(self, data: Dict[str, Any]) -> None:
        """Write task metadata to metadata.json.

        Args:
            data: Dictionary containing task metadata

        The metadata typically includes:
        - task_id: Task identifier
        - source: Task source (webhook, dashboard, etc.)
        - provider: Provider name (github, jira, slack, etc.)
        - created_at: Task creation timestamp
        - status: Current task status
        - assigned_agent: Agent handling the task
        - model: Model being used

        Raises:
            TypeError: If data is not JSON serializable
            OSError: If file cannot be written
        """
        metadata_file = self._log_dir / "metadata.json"
        self._safe_write_json(metadata_file, data, "metadata")

    def write_input(self, data: Dict[str, Any]) -> None:
        """Write task input to 01-input.json.

        Args:
            data: Dictionary containing task input

        The input typically includes:
        - message: User input or webhook trigger message
        - source_metadata: Additional metadata from the source

        Raises:
            TypeError: If data is not JSON serializable
            OSError: If file cannot be written
        """
        input_file = self._log_dir / "01-input.json"
        self._safe_write_json(input_file, data, "input")

    def append_webhook_event(self, event: Dict[str, Any]) -> None:
        """Append webhook event to 02-webhook-flow.jsonl.

        Args:
            event: Dictionary containing webhook event data

        Each event is written as a single JSON line. Events typically include:
        - timestamp: Event timestamp
        - stage: Webhook processing stage (received, validated, task_created, etc.)
        - Additional stage-specific data

        Note:
            Does not raise exceptions - logs errors but continues execution
            to prevent logging failures from blocking task execution.
        """
        webhook_file = self._log_dir / "02-webhook-flow.jsonl"
        self._safe_append_jsonl(webhook_file, event, "webhook_event", stage=event.get("stage"))

    def append_agent_output(self, output: Dict[str, Any]) -> None:
        """Append agent output to 03-agent-output.jsonl.

        Args:
            output: Dictionary containing agent output data

        Each output is written as a single JSON line. Outputs typically include:
        - timestamp: Output timestamp
        - type: Output type (system, thinking, tool_call, tool_result, message)
        - Additional type-specific data (content, tool, params, etc.)

        Note:
            Does not raise exceptions - logs errors but continues execution
            to prevent logging failures from blocking task execution.
        """
        output_file = self._log_dir / "03-agent-output.jsonl"
        self._safe_append_jsonl(output_file, output, "agent_output", output_type=output.get("type"))

    def write_final_result(self, data: Dict[str, Any]) -> None:
        """Write final task result to 04-final-result.json.

        Args:
            data: Dictionary containing final result data

        The result typically includes:
        - success: Boolean indicating task success
        - result: Final output text or None
        - error: Error message if failed, or None
        - metrics: Dictionary with cost, tokens, duration, etc.
        - completed_at: Completion timestamp

        Note:
            Does not raise exceptions - logs errors but continues execution
            to prevent logging failures from blocking task completion.
        """
        result_file = self._log_dir / "04-final-result.json"
        try:
            self._write_json_file_atomic(result_file, data)
            logger.debug("task_result_written", task_id=self.task_id, success=data.get("success"))
        except Exception as e:
            logger.error("task_result_write_failed", task_id=self.task_id, error=str(e))
            # Don't raise - final result logging should not block task completion

    def _safe_write_json(self, file_path: Path, data: Dict[str, Any], log_name: str) -> None:
        """Safely write JSON with error handling and logging.

        Args:
            file_path: Path to the JSON file
            data: Data to write
            log_name: Name for logging (e.g., "metadata", "input")

        Raises:
            TypeError: If data is not JSON serializable
            OSError: If file cannot be written
        """
        try:
            self._write_json_file_atomic(file_path, data)
            logger.debug(f"task_{log_name}_written", task_id=self.task_id)
        except (TypeError, OSError) as e:
            logger.error(f"task_{log_name}_write_failed", task_id=self.task_id, error=str(e), error_type=type(e).__name__)
            raise

    def _safe_append_jsonl(self, file_path: Path, data: Dict[str, Any], log_name: str, **extra_log_data) -> None:
        """Safely append JSONL with error handling and logging (non-blocking).

        Args:
            file_path: Path to the JSONL file
            data: Data to append
            log_name: Name for logging (e.g., "webhook_event", "agent_output")
            **extra_log_data: Additional data to include in log messages
        """
        try:
            self._append_jsonl_line(file_path, data)
            logger.debug(f"{log_name}_appended", task_id=self.task_id, **extra_log_data)
        except Exception as e:
            logger.error(f"{log_name}_append_failed", task_id=self.task_id, error=str(e), error_type=type(e).__name__)
            # Don't raise - logging failures should not block task execution

    def _write_json_file_atomic(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to a JSON file atomically using temp file + rename.

        This prevents partial writes if the process is interrupted.
        Uses the same directory as the target file to ensure atomic rename
        (rename is atomic only within the same filesystem).

        Args:
            file_path: Path to the JSON file
            data: Data to write

        Raises:
            TypeError: If data is not JSON serializable
            OSError: If file cannot be written
        """
        # Create temp file in same directory for atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp"
        )

        try:
            # Write to temp file
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

            # Atomic rename
            os.rename(temp_path, file_path)
        except:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except:
                pass
            raise

    def _append_jsonl_line(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Append a JSON line to a JSONL file.

        Uses append mode which is atomic on POSIX systems for writes
        smaller than PIPE_BUF (typically 4KB+).

        Args:
            file_path: Path to the JSONL file
            data: Data to append as a single line

        Raises:
            TypeError: If data is not JSON serializable
            OSError: If file cannot be written
        """
        json_line = json.dumps(data) + "\n"
        with open(file_path, "a") as f:
            f.write(json_line)
