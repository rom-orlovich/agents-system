"""Conversation data factory for testing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .task_factory import Task


@dataclass
class ConversationMessage:
    """Conversation message model."""

    message_id: str
    role: str
    content: str
    task_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation model for testing business logic."""

    conversation_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_archived: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    total_cost_usd: float = 0.0
    total_tasks: int = 0
    total_duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    messages: list[ConversationMessage] = field(default_factory=list)
    _tasks: list[Task] = field(default_factory=list)

    def add_message(
        self,
        message_id: str,
        role: str,
        content: str,
        task_id: str | None = None,
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(
            message_id=message_id,
            role=role,
            content=content,
            task_id=task_id,
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message

    def add_task(self, task: Task) -> None:
        """Add a task and update aggregated metrics."""
        self._tasks.append(task)
        self.total_cost_usd += task.cost_usd
        self.total_tasks += 1
        self.total_duration_seconds += task.duration_seconds

        if task.started_at:
            if self.started_at is None or task.started_at < self.started_at:
                self.started_at = task.started_at

        if task.completed_at:
            if self.completed_at is None or task.completed_at > self.completed_at:
                self.completed_at = task.completed_at

        self.updated_at = datetime.now(timezone.utc)

    def archive(self) -> None:
        """Archive the conversation."""
        self.is_archived = True
        self.updated_at = datetime.now(timezone.utc)

    def get_messages_ordered(self) -> list[ConversationMessage]:
        """Get messages ordered chronologically."""
        return sorted(self.messages, key=lambda m: m.created_at)


class ConversationFactory:
    """Factory for creating test conversations."""

    _counter: int = 0
    _message_counter: int = 0

    @classmethod
    def create(
        cls,
        conversation_id: str | None = None,
        user_id: str = "test-user",
        title: str = "Test Conversation",
        **kwargs,
    ) -> Conversation:
        """Create a test conversation."""
        cls._counter += 1
        if conversation_id is None:
            conversation_id = f"conv-{cls._counter:03d}"

        return Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            **kwargs,
        )

    @classmethod
    def create_with_messages(
        cls,
        message_count: int = 3,
        **kwargs,
    ) -> Conversation:
        """Create a conversation with messages."""
        conversation = cls.create(**kwargs)

        roles = ["user", "assistant"]
        for i in range(message_count):
            cls._message_counter += 1
            conversation.add_message(
                message_id=f"msg-{cls._message_counter:03d}",
                role=roles[i % 2],
                content=f"Test message {i + 1}",
            )

        return conversation

    @classmethod
    def create_archived(cls, **kwargs) -> Conversation:
        """Create an archived conversation."""
        conversation = cls.create(**kwargs)
        conversation.archive()
        return conversation

    @classmethod
    def reset(cls) -> None:
        """Reset the factory counters."""
        cls._counter = 0
        cls._message_counter = 0
