from pathlib import Path
from .types import JsonDict, JsonValue
from datetime import datetime, timezone
import structlog
import json
import os
import tempfile

logger = structlog.get_logger()


class TaskLogger:
    _instances: dict[str, "TaskLogger"] = {}

    def __init__(self, task_id: str, logs_base_dir: Path | None = None):
        self.task_id = task_id
        if logs_base_dir is None:
            logs_base_dir = Path(os.getenv("TASK_LOGS_DIR", "/data/logs/tasks"))
        self.logs_base_dir = Path(logs_base_dir)
        self._log_dir = self.logs_base_dir / task_id
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(task_id=task_id)

    @classmethod
    def get_or_create(
        cls, task_id: str, logs_base_dir: Path | None = None
    ) -> "TaskLogger":
        if task_id not in cls._instances:
            cls._instances[task_id] = cls(task_id, logs_base_dir)
        return cls._instances[task_id]

    def log_agent_output(self, output_type: str, **data: JsonValue | JsonDict | list) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": output_type,
            "task_id": self.task_id,
            **data,
        }
        self._append_jsonl("04-agent-output.jsonl", event)
        self.logger.info("agent_output", output_type=output_type, **data)

    def log_microservice_call(self, service: str, stage: str, **data: JsonValue | JsonDict | list) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": service,
            "stage": stage,
            "task_id": self.task_id,
            **data,
        }
        self._append_jsonl("05-microservices-flow.jsonl", event)
        self.logger.info("microservice_call", service=service, stage=stage, **data)

    def write_final_result(self, data: JsonDict) -> None:
        result_file = self._log_dir / "06-final-result.json"
        self._safe_write_json(result_file, data)

    def _safe_write_json(self, file_path: Path, data: JsonDict) -> None:
        try:
            fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent, prefix=f".{file_path.name}.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.rename(temp_path, file_path)
            except Exception:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
        except Exception as e:
            self.logger.error(
                "task_logger_write_failed", file=str(file_path), error=str(e)
            )

    def _append_jsonl(self, filename: str, data: JsonDict) -> None:
        try:
            file_path = self._log_dir / filename
            json_line = json.dumps(data) + "\n"
            with open(file_path, "a") as f:
                f.write(json_line)
        except Exception as e:
            self.logger.error("task_logger_append_failed", file=filename, error=str(e))
