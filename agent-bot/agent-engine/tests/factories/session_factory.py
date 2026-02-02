"""Session data factory for testing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .task_factory import Task


@dataclass
class Session:
    """Session model for testing business logic."""

    session_id: str
    user_id: str
    machine_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    disconnected_at: datetime | None = None
    total_cost_usd: float = 0.0
    total_tasks: int = 0
    active: bool = True

    _tasks: list[Task] = field(default_factory=list)

    def add_completed_task(self, task: Task) -> None:
        """Add a completed task and update metrics."""
        self._tasks.append(task)
        self.total_cost_usd += task.cost_usd
        self.total_tasks += 1

    def disconnect(self) -> None:
        """Mark session as disconnected."""
        self.disconnected_at = datetime.now(timezone.utc)

    def set_rate_limited(self) -> None:
        """Mark session as rate limited."""
        self.active = False

    def validate(self) -> list[str]:
        """Validate session data."""
        errors = []
        if not self.user_id:
            errors.append("user_id is required")
        if not self.machine_id:
            errors.append("machine_id is required")
        return errors


class SessionFactory:
    """Factory for creating test sessions."""

    _counter: int = 0

    @classmethod
    def create(
        cls,
        session_id: str | None = None,
        user_id: str = "test-user",
        machine_id: str = "test-machine",
        **kwargs,
    ) -> Session:
        """Create a test session."""
        cls._counter += 1
        if session_id is None:
            session_id = f"session-{cls._counter:03d}"

        return Session(
            session_id=session_id,
            user_id=user_id,
            machine_id=machine_id,
            **kwargs,
        )

    @classmethod
    def create_active(cls, **kwargs) -> Session:
        """Create an active session."""
        return cls.create(active=True, **kwargs)

    @classmethod
    def create_disconnected(cls, **kwargs) -> Session:
        """Create a disconnected session."""
        session = cls.create(**kwargs)
        session.disconnect()
        return session

    @classmethod
    def create_rate_limited(cls, **kwargs) -> Session:
        """Create a rate-limited session."""
        session = cls.create(**kwargs)
        session.set_rate_limited()
        return session

    @classmethod
    def reset(cls) -> None:
        """Reset the factory counter."""
        cls._counter = 0
