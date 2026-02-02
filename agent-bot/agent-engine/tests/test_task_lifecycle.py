"""Tests for task lifecycle business logic.

Tests the task state machine that governs all agent executions.
"""

import pytest

from .factories.task_factory import (
    TaskStatus,
    InvalidTransitionError,
    VALID_TRANSITIONS,
)


class TestTaskCreation:
    """Tests for task creation."""

    def test_task_created_in_queued_status(self, task_factory):
        """Business requirement: New tasks start as QUEUED."""
        task = task_factory.create(input_message="Fix authentication bug")

        assert task.status == TaskStatus.QUEUED
        assert task.input_message == "Fix authentication bug"
        assert task.started_at is None
        assert task.completed_at is None

    def test_task_requires_input_message(self, task_factory):
        """Business requirement: Tasks must have work to do."""
        task = task_factory.create(input_message="")
        assert task.input_message == ""

        task_with_message = task_factory.create(input_message="Do something")
        assert task_with_message.input_message == "Do something"

    def test_task_has_unique_id(self, task_factory):
        """Business requirement: Each task has unique identifier."""
        task1 = task_factory.create()
        task2 = task_factory.create()

        assert task1.task_id != task2.task_id


class TestTaskTransitions:
    """Tests for task state transitions."""

    def test_task_transitions_to_running_when_picked_up(self, task_factory):
        """Business requirement: Processing starts transitions to RUNNING."""
        task = task_factory.create(input_message="Fix bug")

        assert task.status == TaskStatus.QUEUED
        assert task.started_at is None

        task.start()

        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_running_task_can_complete(self, task_factory):
        """Business requirement: Running tasks can complete successfully."""
        task = task_factory.create(input_message="Fix bug")
        task.start()
        task.complete(result="Bug fixed", cost_usd=0.05)

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == "Bug fixed"
        assert task.cost_usd == 0.05

    def test_running_task_can_fail(self, task_factory):
        """Business requirement: Running tasks can fail with error."""
        task = task_factory.create(input_message="Fix bug")
        task.start()
        task.fail(error="Timeout exceeded")

        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None
        assert task.error == "Timeout exceeded"

    def test_running_task_can_wait_for_input(self, task_factory):
        """Business requirement: Long tasks may need user input."""
        task = task_factory.create(input_message="Complex task")
        task.start()
        task.wait_for_input()

        assert task.status == TaskStatus.WAITING_INPUT

    def test_waiting_task_can_resume(self, task_factory):
        """Business requirement: Input received resumes execution."""
        task = task_factory.create(input_message="Complex task")
        task.start()
        task.wait_for_input()

        assert task.status == TaskStatus.WAITING_INPUT

        task.resume()

        assert task.status == TaskStatus.RUNNING

    def test_task_can_be_cancelled_from_queued(self, task_factory):
        """Business requirement: Queued tasks can be cancelled."""
        task = task_factory.create(input_message="Pending task")
        task.cancel()

        assert task.status == TaskStatus.CANCELLED

    def test_task_can_be_cancelled_from_running(self, task_factory):
        """Business requirement: Running tasks can be cancelled."""
        task = task_factory.create(input_message="Active task")
        task.start()
        task.cancel()

        assert task.status == TaskStatus.CANCELLED


class TestTerminalStates:
    """Tests for terminal (final) states."""

    def test_task_cannot_transition_from_completed(self, task_factory):
        """Business requirement: Completed tasks are final."""
        task = task_factory.create_completed()

        assert task.status == TaskStatus.COMPLETED

        with pytest.raises(InvalidTransitionError):
            task.start()

        with pytest.raises(InvalidTransitionError):
            task.fail(error="Should not work")

        with pytest.raises(InvalidTransitionError):
            task.cancel()

    def test_task_cannot_transition_from_failed(self, task_factory):
        """Business requirement: Failed tasks are final."""
        task = task_factory.create_failed()

        assert task.status == TaskStatus.FAILED

        with pytest.raises(InvalidTransitionError):
            task.start()

        with pytest.raises(InvalidTransitionError):
            task.complete(result="Should not work")

        with pytest.raises(InvalidTransitionError):
            task.cancel()

    def test_task_cannot_transition_from_cancelled(self, task_factory):
        """Business requirement: Cancelled tasks are final."""
        task = task_factory.create(input_message="Task to cancel")
        task.cancel()

        assert task.status == TaskStatus.CANCELLED

        with pytest.raises(InvalidTransitionError):
            task.start()

        with pytest.raises(InvalidTransitionError):
            task.complete(result="Should not work")


class TestTaskMetrics:
    """Tests for task metrics tracking."""

    def test_task_duration_calculated_on_completion(self, task_factory):
        """Business requirement: Duration tracked for analytics."""
        task = task_factory.create(input_message="Timed task")
        task.start()

        task.complete(result="Done", cost_usd=0.05)

        assert task.duration_seconds >= 0

    def test_task_cost_accumulated_correctly(self, task_factory):
        """Business requirement: Cost tracking for billing."""
        task = task_factory.create(input_message="Billable task")
        task.start()
        task.complete(
            result="Done",
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
        )

        assert task.cost_usd == 0.05
        assert task.input_tokens == 1000
        assert task.output_tokens == 500


class TestCompleteTaskFlow:
    """Tests for complete task lifecycle flows."""

    def test_complete_task_flow_success(self, task_factory):
        """Business requirement: Tasks flow from QUEUED -> RUNNING -> COMPLETED."""
        task = task_factory.create(input_message="Fix authentication bug")

        assert task.status == TaskStatus.QUEUED
        assert task.started_at is None

        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        task.complete(result="Bug fixed", cost_usd=0.05)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.duration_seconds >= 0
        assert task.cost_usd == 0.05

    def test_complete_task_flow_with_user_input(self, task_factory):
        """Business requirement: Tasks can pause for user input."""
        task = task_factory.create(input_message="Interactive task")

        task.start()
        assert task.status == TaskStatus.RUNNING

        task.wait_for_input()
        assert task.status == TaskStatus.WAITING_INPUT

        task.resume()
        assert task.status == TaskStatus.RUNNING

        task.complete(result="Completed after user input")
        assert task.status == TaskStatus.COMPLETED

    def test_complete_task_flow_failure(self, task_factory):
        """Business requirement: Tasks can fail with error details."""
        task = task_factory.create(input_message="Failing task")

        task.start()
        task.fail(error="API rate limit exceeded")

        assert task.status == TaskStatus.FAILED
        assert task.error == "API rate limit exceeded"
        assert task.duration_seconds >= 0


class TestValidTransitions:
    """Tests for transition validation matrix."""

    def test_all_valid_transitions_defined(self):
        """Verify all states have defined transitions."""
        for status in TaskStatus:
            assert status in VALID_TRANSITIONS

    def test_terminal_states_have_no_transitions(self):
        """Terminal states should have empty transition sets."""
        terminal_states = [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]
        for state in terminal_states:
            assert VALID_TRANSITIONS[state] == set()

    def test_non_terminal_states_have_transitions(self):
        """Non-terminal states should have valid transitions."""
        non_terminal = [
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.WAITING_INPUT,
        ]
        for state in non_terminal:
            assert len(VALID_TRANSITIONS[state]) > 0
