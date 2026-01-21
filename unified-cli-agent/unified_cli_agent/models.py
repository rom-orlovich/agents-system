"""
Data models for unified CLI agent system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    """Task status states"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task data structure"""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = field(default=TaskStatus.QUEUED, init=False)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = field(default=None, init=False)
    completed_at: Optional[datetime] = field(default=None, init=False)
    error: Optional[str] = field(default=None, init=False)
    result: Optional[Dict[str, Any]] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize mutable fields"""
        if not hasattr(self, 'status'):
            self.status = TaskStatus.QUEUED
        if not hasattr(self, 'started_at'):
            self.started_at = None
        if not hasattr(self, 'completed_at'):
            self.completed_at = None
        if not hasattr(self, 'error'):
            self.error = None
        if not hasattr(self, 'result'):
            self.result = None

    def __lt__(self, other: 'Task') -> bool:
        """
        Compare tasks for priority queue ordering.
        Lower priority value = higher priority (CRITICAL=1 > LOW=4)
        Within same priority, older tasks come first (FIFO)
        """
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


@dataclass
class TaskMetrics:
    """Metrics about task processing"""
    queue_size: int
    by_priority: Dict[TaskPriority, int]
    by_status: Dict[TaskStatus, int]
    total_completed: int
    total_failed: int
    total_cancelled: int
    history_size: int
