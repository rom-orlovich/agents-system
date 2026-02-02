"""Task data factory for testing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    """Task status enum matching business logic."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_INPUT: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


@dataclass
class Task:
    """Task model for testing business logic."""

    task_id: str
    input_message: str
    status: TaskStatus = TaskStatus.QUEUED
    session_id: str | None = None
    agent_type: str = "executor"
    source: str = "dashboard"
    source_metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    result: str | None = None
    error: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0

    def _validate_transition(self, new_status: TaskStatus) -> None:
        """Validate state transition."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to {new_status}"
            )

    def start(self) -> None:
        """Transition task to RUNNING status."""
        self._validate_transition(TaskStatus.RUNNING)
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def wait_for_input(self) -> None:
        """Transition task to WAITING_INPUT status."""
        self._validate_transition(TaskStatus.WAITING_INPUT)
        self.status = TaskStatus.WAITING_INPUT

    def resume(self) -> None:
        """Resume task from WAITING_INPUT to RUNNING."""
        self._validate_transition(TaskStatus.RUNNING)
        self.status = TaskStatus.RUNNING

    def complete(
        self,
        result: str = "",
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Transition task to COMPLETED status."""
        self._validate_transition(TaskStatus.COMPLETED)
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result
        self.cost_usd = cost_usd
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        if self.started_at:
            self.duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

    def fail(self, error: str) -> None:
        """Transition task to FAILED status."""
        self._validate_transition(TaskStatus.FAILED)
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error
        if self.started_at:
            self.duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

    def cancel(self) -> None:
        """Transition task to CANCELLED status."""
        self._validate_transition(TaskStatus.CANCELLED)
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)


class TaskFactory:
    """Factory for creating test tasks."""

    _counter: int = 0

    @classmethod
    def create(
        cls,
        task_id: str | None = None,
        input_message: str = "Test task",
        status: TaskStatus = TaskStatus.QUEUED,
        session_id: str | None = None,
        agent_type: str = "executor",
        source: str = "dashboard",
        **kwargs,
    ) -> Task:
        """Create a test task."""
        cls._counter += 1
        if task_id is None:
            task_id = f"task-{cls._counter:03d}"

        return Task(
            task_id=task_id,
            input_message=input_message,
            status=status,
            session_id=session_id,
            agent_type=agent_type,
            source=source,
            **kwargs,
        )

    @classmethod
    def create_queued(cls, **kwargs) -> Task:
        """Create a task in QUEUED status."""
        return cls.create(status=TaskStatus.QUEUED, **kwargs)

    @classmethod
    def create_running(cls, **kwargs) -> Task:
        """Create a task in RUNNING status."""
        task = cls.create(**kwargs)
        task.start()
        return task

    @classmethod
    def create_completed(
        cls,
        result: str = "Task completed successfully",
        cost_usd: float = 0.05,
        **kwargs,
    ) -> Task:
        """Create a task in COMPLETED status."""
        task = cls.create(**kwargs)
        task.start()
        task.complete(result=result, cost_usd=cost_usd)
        return task

    @classmethod
    def create_failed(cls, error: str = "Task failed", **kwargs) -> Task:
        """Create a task in FAILED status."""
        task = cls.create(**kwargs)
        task.start()
        task.fail(error=error)
        return task

    @classmethod
    def reset(cls) -> None:
        """Reset the factory counter."""
        cls._counter = 0
