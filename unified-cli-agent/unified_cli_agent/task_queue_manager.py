"""
Task Queue Manager

Centralized queue for all incoming tasks.
Manages task lifecycle, priority, and history.
"""

import asyncio
import heapq
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, List, Dict
from threading import Lock

from .models import Task, TaskStatus, TaskPriority, TaskMetrics


class TaskQueueManager:
    """
    Centralized queue for all incoming tasks.
    Supports priority-based scheduling, task deduplication,
    and maintains history of completed tasks.
    """

    def __init__(
        self,
        max_queue_size: int = 100,
        max_history_size: int = 1000
    ):
        """
        Initialize TaskQueueManager

        Args:
            max_queue_size: Maximum number of tasks in queue
            max_history_size: Maximum number of tasks to keep in history
        """
        self.max_queue_size = max_queue_size
        self.max_history_size = max_history_size

        # Priority queue (min heap) for pending tasks
        self._queue: List[Task] = []

        # Map of task_id to task for quick lookups
        self._tasks: Dict[str, Task] = {}

        # History of completed/failed tasks (FIFO)
        self._history: deque = deque(maxlen=max_history_size)

        # Lock for thread-safe operations
        self._lock = Lock()

        # Async notification event for waiting consumers
        self._task_available = asyncio.Event()

        # Counters for metrics
        self._total_completed = 0
        self._total_failed = 0
        self._total_cancelled = 0

    def queue_size(self) -> int:
        """Get current queue size"""
        with self._lock:
            return len([t for t in self._tasks.values() if t.status == TaskStatus.QUEUED])

    def enqueue_task(self, task: Task) -> str:
        """
        Enqueue a task

        Args:
            task: Task to enqueue

        Returns:
            task_id: ID of the enqueued task

        Raises:
            ValueError: If task with same ID already exists
            RuntimeError: If queue is full
        """
        with self._lock:
            # Check for duplicate task ID
            if task.task_id in self._tasks:
                raise ValueError(f"Task with ID '{task.task_id}' already exists")

            # Check queue capacity
            current_queued = len([t for t in self._tasks.values() if t.status == TaskStatus.QUEUED])
            if current_queued >= self.max_queue_size:
                raise RuntimeError(f"Queue is full (max size: {self.max_queue_size})")

            # Add to queue and task map
            heapq.heappush(self._queue, task)
            self._tasks[task.task_id] = task

            # Notify async consumers
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(self._task_available.set)
            except RuntimeError:
                # No event loop running, that's fine
                pass

            return task.task_id

    def dequeue_task(self) -> Optional[Task]:
        """
        Dequeue the highest priority task

        Returns:
            Task if available, None if queue is empty
        """
        with self._lock:
            # Remove completed/failed tasks from heap
            while self._queue and self._queue[0].status != TaskStatus.QUEUED:
                heapq.heappop(self._queue)

            # Get highest priority task
            if not self._queue:
                return None

            task = heapq.heappop(self._queue)

            # Mark task as in progress
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()

            return task

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get status of a task

        Args:
            task_id: Task ID

        Returns:
            TaskStatus if task exists, None otherwise
        """
        with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get full task information

        Args:
            task_id: Task ID

        Returns:
            Task if exists, None otherwise
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update task status

        Args:
            task_id: Task ID
            status: New status

        Raises:
            ValueError: If task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")

            task.status = status

            # Set started_at if transitioning to IN_PROGRESS
            if status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now()

    def complete_task(self, task_id: str, result: Dict) -> None:
        """
        Mark task as completed

        Args:
            task_id: Task ID
            result: Task result data

        Raises:
            ValueError: If task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

            self._total_completed += 1
            self._move_to_history(task)

    def fail_task(self, task_id: str, error: str) -> None:
        """
        Mark task as failed

        Args:
            task_id: Task ID
            error: Error message

        Raises:
            ValueError: If task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")

            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now()

            self._total_failed += 1
            self._move_to_history(task)

    def _move_to_history(self, task: Task) -> None:
        """
        Move task to history (called with lock held)

        Args:
            task: Task to move to history
        """
        # If history is full, remove oldest task from both history and _tasks map
        if len(self._history) >= self.max_history_size:
            oldest_task = self._history[0]  # deque removes from left when full
            if oldest_task.task_id in self._tasks:
                del self._tasks[oldest_task.task_id]

        self._history.append(task)
        # Task stays in _tasks map for retrieval (until evicted from history)

    def get_history(self, limit: Optional[int] = None) -> List[Task]:
        """
        Get task history

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of historical tasks (most recent first)
        """
        with self._lock:
            history_list = list(self._history)
            history_list.reverse()  # Most recent first
            if limit:
                return history_list[:limit]
            return history_list

    def get_metrics(self) -> Dict:
        """
        Get queue metrics and statistics

        Returns:
            Dictionary with metrics
        """
        with self._lock:
            # Count by priority
            by_priority = defaultdict(int)
            by_status = defaultdict(int)
            queued_count = 0

            for task in self._tasks.values():
                if task.status == TaskStatus.QUEUED:
                    by_priority[task.priority] += 1
                    queued_count += 1
                by_status[task.status] += 1

            return {
                "queue_size": queued_count,
                "by_priority": dict(by_priority),
                "by_status": dict(by_status),
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_cancelled": self._total_cancelled,
                "history_size": len(self._history),
            }

    # Async methods
    async def enqueue_task_async(self, task: Task) -> str:
        """
        Async version of enqueue_task

        Args:
            task: Task to enqueue

        Returns:
            task_id: ID of the enqueued task
        """
        return self.enqueue_task(task)

    async def dequeue_task_async(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Async version of dequeue_task that waits for tasks

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Task if available within timeout, None otherwise
        """
        # Try immediate dequeue
        task = self.dequeue_task()
        if task:
            return task

        # Wait for task to become available
        if timeout:
            try:
                await asyncio.wait_for(self._task_available.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
        else:
            await self._task_available.wait()

        # Clear event for next wait
        self._task_available.clear()

        # Try dequeue again
        return self.dequeue_task()
