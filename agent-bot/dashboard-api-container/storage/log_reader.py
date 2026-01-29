from pathlib import Path
import json
import os
from api.models import TaskLogsResponse, TaskLogEntry
import structlog

logger = structlog.get_logger()


class LogReader:
    def __init__(self, logs_base_dir: Path | None = None):
        if logs_base_dir is None:
            logs_base_dir = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
        self.logs_base_dir = Path(logs_base_dir)

    async def read_task_logs(self, task_id: str) -> TaskLogsResponse:
        task_log_dir = self.logs_base_dir / task_id

        if not task_log_dir.exists():
            raise FileNotFoundError(f"Task logs not found for {task_id}")

        metadata = self._read_json_file(task_log_dir / "metadata.json")
        input_data = self._read_json_file(task_log_dir / "01-input.json")
        final_result = self._read_json_file(task_log_dir / "06-final-result.json")

        webhook_flow = self._read_jsonl_file(task_log_dir / "02-webhook-flow.jsonl")
        queue_flow = self._read_jsonl_file(task_log_dir / "03-queue-flow.jsonl")
        agent_output = self._read_jsonl_file(task_log_dir / "04-agent-output.jsonl")
        microservices_flow = self._read_jsonl_file(
            task_log_dir / "05-microservices-flow.jsonl"
        )

        return TaskLogsResponse(
            task_id=task_id,
            metadata=metadata,
            input_data=input_data,
            webhook_flow=webhook_flow,
            queue_flow=queue_flow,
            agent_output=agent_output,
            microservices_flow=microservices_flow,
            final_result=final_result,
        )

    def _read_json_file(self, file_path: Path) -> dict[str, str | int | bool | dict] | None:
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error("read_json_failed", file=str(file_path), error=str(e))
            return None

    def _read_jsonl_file(self, file_path: Path) -> list[TaskLogEntry]:
        if not file_path.exists():
            return []

        entries = []
        try:
            with open(file_path) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        entries.append(
                            TaskLogEntry(
                                timestamp=data.get("timestamp", ""),
                                stage=data.get("stage", ""),
                                data=data,
                            )
                        )
        except Exception as e:
            logger.error("read_jsonl_failed", file=str(file_path), error=str(e))

        return entries
