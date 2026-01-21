"""
TDD Tests for TaskQueueManager

Test-driven development for the centralized task queue manager.
"""

import pytest
from datetime import datetime, timedelta
import asyncio

# Import actual models from the package
from unified_cli_agent.models import Task, TaskPriority, TaskStatus


# TDD Tests
class TestTaskQueueManagerCreation:
    """Test TaskQueueManager initialization"""

    def test_can_create_task_queue_manager(self):
        """Should be able to create a TaskQueueManager instance"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        assert manager is not None

    def test_task_queue_manager_has_max_size(self):
        """TaskQueueManager should have configurable max size"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager(max_queue_size=100)
        assert manager.max_queue_size == 100

    def test_task_queue_manager_has_history_size(self):
        """TaskQueueManager should have configurable history size"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager(max_history_size=1000)
        assert manager.max_history_size == 1000

    def test_task_queue_manager_starts_empty(self):
        """TaskQueueManager should start with empty queue"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        assert manager.queue_size() == 0


class TestTaskEnqueuing:
    """Test enqueuing tasks"""

    def test_can_enqueue_task(self):
        """Should be able to enqueue a task"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(
            task_id="test-1",
            task_type="discovery",
            data={"repo": "test/repo"}
        )

        task_id = manager.enqueue_task(task)
        assert task_id == "test-1"
        assert manager.queue_size() == 1

    def test_enqueue_increases_queue_size(self):
        """Enqueuing tasks should increase queue size"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        for i in range(5):
            task = Task(
                task_id=f"test-{i}",
                task_type="discovery",
                data={}
            )
            manager.enqueue_task(task)

        assert manager.queue_size() == 5

    def test_cannot_enqueue_duplicate_task_id(self):
        """Should not be able to enqueue task with duplicate ID"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task1 = Task(task_id="test-1", task_type="discovery", data={})
        task2 = Task(task_id="test-1", task_type="planning", data={})

        manager.enqueue_task(task1)

        with pytest.raises(ValueError, match="already exists"):
            manager.enqueue_task(task2)

    def test_cannot_exceed_max_queue_size(self):
        """Should not be able to exceed max queue size"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager(max_queue_size=3)

        for i in range(3):
            task = Task(task_id=f"test-{i}", task_type="discovery", data={})
            manager.enqueue_task(task)

        task4 = Task(task_id="test-4", task_type="discovery", data={})
        with pytest.raises(RuntimeError, match="Queue is full"):
            manager.enqueue_task(task4)


class TestTaskDequeuing:
    """Test dequeuing tasks"""

    def test_can_dequeue_task(self):
        """Should be able to dequeue a task"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)

        dequeued = manager.dequeue_task()
        assert dequeued is not None
        assert dequeued.task_id == "test-1"
        assert manager.queue_size() == 0

    def test_dequeue_returns_none_when_empty(self):
        """Dequeue should return None when queue is empty"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        dequeued = manager.dequeue_task()
        assert dequeued is None

    def test_dequeue_respects_priority_order(self):
        """Dequeue should return tasks in priority order"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Add tasks in random priority order
        tasks = [
            Task("low", "discovery", {}, TaskPriority.LOW),
            Task("critical", "discovery", {}, TaskPriority.CRITICAL),
            Task("normal", "discovery", {}, TaskPriority.NORMAL),
            Task("high", "discovery", {}, TaskPriority.HIGH),
        ]

        for task in tasks:
            manager.enqueue_task(task)

        # Should dequeue in priority order: CRITICAL > HIGH > NORMAL > LOW
        assert manager.dequeue_task().task_id == "critical"
        assert manager.dequeue_task().task_id == "high"
        assert manager.dequeue_task().task_id == "normal"
        assert manager.dequeue_task().task_id == "low"

    def test_dequeue_fifo_within_same_priority(self):
        """Tasks with same priority should be dequeued FIFO"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Add multiple tasks with same priority
        for i in range(5):
            task = Task(f"test-{i}", "discovery", {}, TaskPriority.NORMAL)
            manager.enqueue_task(task)

        # Should dequeue in FIFO order
        for i in range(5):
            assert manager.dequeue_task().task_id == f"test-{i}"


class TestTaskStatusQueries:
    """Test querying task status"""

    def test_can_get_task_status(self):
        """Should be able to get task status"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)

        status = manager.get_task_status("test-1")
        assert status == TaskStatus.QUEUED

    def test_get_status_returns_none_for_unknown_task(self):
        """Getting status of unknown task should return None"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        status = manager.get_task_status("unknown")
        assert status is None

    def test_can_get_full_task_info(self):
        """Should be able to get full task information"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(
            task_id="test-1",
            task_type="discovery",
            data={"repo": "test/repo"},
            priority=TaskPriority.HIGH
        )
        manager.enqueue_task(task)

        task_info = manager.get_task("test-1")
        assert task_info is not None
        assert task_info.task_id == "test-1"
        assert task_info.task_type == "discovery"
        assert task_info.priority == TaskPriority.HIGH
        assert task_info.data["repo"] == "test/repo"


class TestTaskStatusUpdates:
    """Test updating task status"""

    def test_can_update_task_status(self):
        """Should be able to update task status"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)

        manager.update_task_status("test-1", TaskStatus.IN_PROGRESS)
        assert manager.get_task_status("test-1") == TaskStatus.IN_PROGRESS

    def test_update_nonexistent_task_raises_error(self):
        """Updating nonexistent task should raise error"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        with pytest.raises(ValueError, match="not found"):
            manager.update_task_status("unknown", TaskStatus.IN_PROGRESS)

    def test_can_mark_task_completed_with_result(self):
        """Should be able to mark task completed with result"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)

        result = {"repos_found": 5, "files_analyzed": 20}
        manager.complete_task("test-1", result)

        task_info = manager.get_task("test-1")
        assert task_info.status == TaskStatus.COMPLETED
        assert task_info.result == result
        assert task_info.completed_at is not None

    def test_can_mark_task_failed_with_error(self):
        """Should be able to mark task failed with error"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)

        error = "API rate limit exceeded"
        manager.fail_task("test-1", error)

        task_info = manager.get_task("test-1")
        assert task_info.status == TaskStatus.FAILED
        assert task_info.error == error
        assert task_info.completed_at is not None


class TestTaskHistory:
    """Test task history management"""

    def test_completed_tasks_moved_to_history(self):
        """Completed tasks should be moved to history"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task(task_id="test-1", task_type="discovery", data={})
        manager.enqueue_task(task)
        manager.complete_task("test-1", {})

        # Task should still be retrievable from history
        task_info = manager.get_task("test-1")
        assert task_info is not None
        assert task_info.status == TaskStatus.COMPLETED

    def test_history_respects_max_size(self):
        """History should not exceed max size"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager(max_history_size=3)

        # Complete 5 tasks
        for i in range(5):
            task = Task(f"test-{i}", "discovery", {})
            manager.enqueue_task(task)
            manager.complete_task(f"test-{i}", {})

        # Only last 3 should be in history
        assert manager.get_task("test-0") is None  # Oldest, evicted
        assert manager.get_task("test-1") is None  # Second oldest, evicted
        assert manager.get_task("test-2") is not None
        assert manager.get_task("test-3") is not None
        assert manager.get_task("test-4") is not None

    def test_can_get_history_list(self):
        """Should be able to get list of historical tasks"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        for i in range(3):
            task = Task(f"test-{i}", "discovery", {})
            manager.enqueue_task(task)
            manager.complete_task(f"test-{i}", {})

        history = manager.get_history()
        assert len(history) == 3
        assert all(t.status == TaskStatus.COMPLETED for t in history)


class TestTaskMetrics:
    """Test task metrics and statistics"""

    def test_can_get_queue_metrics(self):
        """Should be able to get queue metrics"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Add tasks with different priorities
        manager.enqueue_task(Task("t1", "discovery", {}, TaskPriority.CRITICAL))
        manager.enqueue_task(Task("t2", "discovery", {}, TaskPriority.NORMAL))
        manager.enqueue_task(Task("t3", "discovery", {}, TaskPriority.NORMAL))

        metrics = manager.get_metrics()
        assert metrics["queue_size"] == 3
        assert metrics["by_priority"][TaskPriority.CRITICAL] == 1
        assert metrics["by_priority"][TaskPriority.NORMAL] == 2

    def test_metrics_include_processing_stats(self):
        """Metrics should include processing statistics"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Complete some tasks
        for i in range(3):
            task = Task(f"test-{i}", "discovery", {})
            manager.enqueue_task(task)
            manager.complete_task(f"test-{i}", {})

        # Fail some tasks
        for i in range(3, 5):
            task = Task(f"test-{i}", "discovery", {})
            manager.enqueue_task(task)
            manager.fail_task(f"test-{i}", "Error")

        metrics = manager.get_metrics()
        assert metrics["total_completed"] == 3
        assert metrics["total_failed"] == 2


class TestAsyncOperations:
    """Test async queue operations"""

    @pytest.mark.asyncio
    async def test_can_enqueue_async(self):
        """Should be able to enqueue tasks asynchronously"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task("test-1", "discovery", {})

        task_id = await manager.enqueue_task_async(task)
        assert task_id == "test-1"

    @pytest.mark.asyncio
    async def test_can_dequeue_async(self):
        """Should be able to dequeue tasks asynchronously"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()
        task = Task("test-1", "discovery", {})
        await manager.enqueue_task_async(task)

        dequeued = await manager.dequeue_task_async()
        assert dequeued.task_id == "test-1"

    @pytest.mark.asyncio
    async def test_async_dequeue_waits_for_tasks(self):
        """Async dequeue should wait for tasks when queue is empty"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Start dequeue operation
        dequeue_task = asyncio.create_task(manager.dequeue_task_async(timeout=1.0))

        # Wait a bit and then enqueue
        await asyncio.sleep(0.1)
        task = Task("test-1", "discovery", {})
        await manager.enqueue_task_async(task)

        # Should get the task
        dequeued = await dequeue_task
        assert dequeued.task_id == "test-1"

    @pytest.mark.asyncio
    async def test_async_dequeue_timeout(self):
        """Async dequeue should timeout if no tasks available"""
        from unified_cli_agent.task_queue_manager import TaskQueueManager

        manager = TaskQueueManager()

        # Should timeout after 0.5 seconds
        dequeued = await manager.dequeue_task_async(timeout=0.5)
        assert dequeued is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
