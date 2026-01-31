"""Tests for session management business logic.

Tests per-user session tracking and cost aggregation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))


class TestSessionCreation:
    """Tests for session creation."""

    def test_session_created_with_defaults(self, session_factory, task_factory):
        """Business requirement: Sessions start with zero metrics."""
        session = session_factory.create(
            user_id="user-1",
            machine_id="machine-1",
        )

        assert session.total_cost_usd == 0.0
        assert session.total_tasks == 0
        assert session.active is True
        assert session.connected_at is not None

    def test_session_requires_user_and_machine(self, session_factory):
        """Business requirement: Valid session needs identity."""
        session = session_factory.create(user_id="", machine_id="machine-1")
        errors = session.validate()
        assert "user_id is required" in errors

        session = session_factory.create(user_id="user-1", machine_id="")
        errors = session.validate()
        assert "machine_id is required" in errors

    def test_session_has_unique_id(self, session_factory):
        """Business requirement: Each session has unique identifier."""
        session1 = session_factory.create()
        session2 = session_factory.create()

        assert session1.session_id != session2.session_id


class TestSessionCostTracking:
    """Tests for session cost aggregation."""

    def test_session_aggregates_task_costs(self, session_factory, task_factory):
        """Business requirement: Per-user cost tracking."""
        session = session_factory.create(user_id="user-1", machine_id="machine-1")

        assert session.total_cost_usd == 0

        task1 = task_factory.create_completed(cost_usd=0.10)
        session.add_completed_task(task1)

        assert session.total_cost_usd == 0.10

        task2 = task_factory.create_completed(cost_usd=0.25)
        session.add_completed_task(task2)

        assert session.total_cost_usd == 0.35

    def test_session_tracks_task_count(self, session_factory, task_factory):
        """Business requirement: Usage metrics."""
        session = session_factory.create()

        assert session.total_tasks == 0

        task1 = task_factory.create_completed()
        session.add_completed_task(task1)
        assert session.total_tasks == 1

        task2 = task_factory.create_completed()
        session.add_completed_task(task2)
        assert session.total_tasks == 2


class TestSessionStatus:
    """Tests for session status management."""

    def test_session_becomes_inactive_on_rate_limit(self, session_factory):
        """Business requirement: Rate limiting protection."""
        session = session_factory.create()

        assert session.active is True

        session.set_rate_limited()

        assert session.active is False

    def test_disconnected_session_preserves_data(self, session_factory, task_factory):
        """Business requirement: Historical data retention."""
        session = session_factory.create()

        task = task_factory.create_completed(cost_usd=0.50)
        session.add_completed_task(task)

        assert session.total_cost_usd == 0.50
        assert session.total_tasks == 1

        session.disconnect()

        assert session.disconnected_at is not None
        assert session.total_cost_usd == 0.50
        assert session.total_tasks == 1

    def test_session_active_by_default(self, session_factory):
        """Business requirement: New sessions are active."""
        session = session_factory.create_active()
        assert session.active is True

    def test_session_can_be_rate_limited(self, session_factory):
        """Business requirement: Sessions can be rate limited."""
        session = session_factory.create_rate_limited()
        assert session.active is False


class TestSessionCostAccumulation:
    """Complete cost accumulation flow tests."""

    def test_session_cost_accumulation_multiple_tasks(
        self, session_factory, task_factory
    ):
        """Business requirement: Session tracks cumulative costs."""
        session = session_factory.create(user_id="user-1", machine_id="machine-1")

        assert session.total_cost_usd == 0
        assert session.total_tasks == 0

        task1 = task_factory.create(session_id=session.session_id)
        task1.start()
        task1.complete(cost_usd=0.10)
        session.add_completed_task(task1)

        assert session.total_cost_usd == 0.10
        assert session.total_tasks == 1

        task2 = task_factory.create(session_id=session.session_id)
        task2.start()
        task2.complete(cost_usd=0.25)
        session.add_completed_task(task2)

        assert session.total_cost_usd == 0.35
        assert session.total_tasks == 2

    def test_failed_tasks_dont_add_cost(self, session_factory, task_factory):
        """Business requirement: Failed tasks don't incur cost."""
        session = session_factory.create()

        task = task_factory.create_failed()
        session.add_completed_task(task)

        assert session.total_cost_usd == 0.0
        assert session.total_tasks == 1
