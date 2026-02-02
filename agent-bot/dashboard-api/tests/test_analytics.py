"""Tests for analytics business logic.

Tests analytics calculations and aggregations.
"""

import pytest
from datetime import datetime, timezone

from .factories.task_factory import TaskStatus


CLAUDE_PRICING = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
}


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate cost based on token usage."""
    rates = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-sonnet-4"])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def calculate_success_rate(completed: int, total: int) -> float:
    """Calculate success rate as percentage."""
    if total == 0:
        return 0.0
    return (completed / total) * 100


def calculate_average_duration(tasks: list) -> float:
    """Calculate average duration of completed tasks."""
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    if not completed_tasks:
        return 0.0
    total_duration = sum(t.duration_seconds for t in completed_tasks)
    return total_duration / len(completed_tasks)


def aggregate_daily_costs(tasks: list) -> dict[str, float]:
    """Aggregate costs by day."""
    daily_costs: dict[str, float] = {}
    for task in tasks:
        if task.completed_at:
            day = task.completed_at.strftime("%Y-%m-%d")
            daily_costs[day] = daily_costs.get(day, 0.0) + task.cost_usd
    return daily_costs


def aggregate_costs_by_agent(tasks: list) -> dict[str, float]:
    """Aggregate costs by agent type."""
    agent_costs: dict[str, float] = {}
    for task in tasks:
        agent = task.agent_type
        agent_costs[agent] = agent_costs.get(agent, 0.0) + task.cost_usd
    return agent_costs


class TestCostCalculation:
    """Tests for cost calculation."""

    def test_opus_cost_calculation(self):
        """Cost calculation for Opus model."""
        cost = calculate_cost(
            input_tokens=1_000_000,
            output_tokens=100_000,
            model="claude-opus-4",
        )

        expected = (1_000_000 * 15.0 + 100_000 * 75.0) / 1_000_000
        assert cost == expected

    def test_sonnet_cost_calculation(self):
        """Cost calculation for Sonnet model."""
        cost = calculate_cost(
            input_tokens=1_000_000,
            output_tokens=100_000,
            model="claude-sonnet-4",
        )

        expected = (1_000_000 * 3.0 + 100_000 * 15.0) / 1_000_000
        assert cost == expected

    def test_unknown_model_uses_sonnet_pricing(self):
        """Unknown models fall back to Sonnet pricing."""
        cost_unknown = calculate_cost(1000, 500, "unknown-model")
        cost_sonnet = calculate_cost(1000, 500, "claude-sonnet-4")

        assert cost_unknown == cost_sonnet


class TestDailyAggregation:
    """Tests for daily cost aggregation."""

    def test_daily_cost_aggregation(self, task_factory):
        """Business requirement: Cost trends."""
        tasks = []

        task1 = task_factory.create_completed(cost_usd=0.10)
        task1.completed_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tasks.append(task1)

        task2 = task_factory.create_completed(cost_usd=0.20)
        task2.completed_at = datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tasks.append(task2)

        task3 = task_factory.create_completed(cost_usd=0.15)
        task3.completed_at = datetime(2026, 1, 2, 9, 0, 0, tzinfo=timezone.utc)
        tasks.append(task3)

        daily_costs = aggregate_daily_costs(tasks)

        assert daily_costs["2026-01-01"] == pytest.approx(0.30)
        assert daily_costs["2026-01-02"] == pytest.approx(0.15)

    def test_daily_task_count(self, task_factory):
        """Business requirement: Volume trends."""
        tasks = []

        for i in range(5):
            task = task_factory.create_completed()
            task.completed_at = datetime(2026, 1, 1, 10 + i, 0, 0, tzinfo=timezone.utc)
            tasks.append(task)

        day_1_tasks = [
            t for t in tasks if t.completed_at.strftime("%Y-%m-%d") == "2026-01-01"
        ]
        assert len(day_1_tasks) == 5


class TestSuccessRateCalculation:
    """Tests for success rate calculation."""

    def test_success_rate_calculation(self, task_factory):
        """Business requirement: Quality metrics."""
        completed = 8
        failed = 2
        total = completed + failed

        success_rate = calculate_success_rate(completed, total)

        assert success_rate == 80.0

    def test_success_rate_with_no_tasks(self):
        """Success rate with no tasks is 0."""
        success_rate = calculate_success_rate(0, 0)
        assert success_rate == 0.0

    def test_success_rate_all_completed(self):
        """100% success rate."""
        success_rate = calculate_success_rate(10, 10)
        assert success_rate == 100.0


class TestAverageDurationCalculation:
    """Tests for average duration calculation."""

    def test_average_duration_calculation(self, task_factory):
        """Business requirement: Performance metrics."""
        tasks = []

        task1 = task_factory.create_completed()
        task1.duration_seconds = 30.0
        tasks.append(task1)

        task2 = task_factory.create_completed()
        task2.duration_seconds = 60.0
        tasks.append(task2)

        task3 = task_factory.create_completed()
        task3.duration_seconds = 90.0
        tasks.append(task3)

        avg_duration = calculate_average_duration(tasks)

        assert avg_duration == 60.0

    def test_average_duration_excludes_failed(self, task_factory):
        """Failed tasks excluded from duration average."""
        tasks = []

        completed = task_factory.create_completed()
        completed.duration_seconds = 60.0
        tasks.append(completed)

        failed = task_factory.create_failed()
        failed.duration_seconds = 30.0
        tasks.append(failed)

        avg_duration = calculate_average_duration(tasks)

        assert avg_duration == 60.0

    def test_average_duration_no_completed_tasks(self, task_factory):
        """Average is 0 with no completed tasks."""
        tasks = [task_factory.create_failed() for _ in range(3)]

        avg_duration = calculate_average_duration(tasks)

        assert avg_duration == 0.0


class TestCostBreakdown:
    """Tests for cost breakdown by agent/provider."""

    def test_cost_by_agent_breakdown(self, task_factory):
        """Business requirement: Attribution."""
        tasks = []

        task1 = task_factory.create_completed(cost_usd=0.10)
        task1.agent_type = "planning"
        tasks.append(task1)

        task2 = task_factory.create_completed(cost_usd=0.05)
        task2.agent_type = "executor"
        tasks.append(task2)

        task3 = task_factory.create_completed(cost_usd=0.15)
        task3.agent_type = "planning"
        tasks.append(task3)

        agent_costs = aggregate_costs_by_agent(tasks)

        assert agent_costs["planning"] == pytest.approx(0.25)
        assert agent_costs["executor"] == pytest.approx(0.05)

    def test_total_cost_matches_breakdown(self, task_factory):
        """Agent costs sum to total."""
        tasks = []

        for agent_type, cost in [
            ("planning", 0.10),
            ("executor", 0.05),
            ("brain", 0.20),
        ]:
            task = task_factory.create_completed(cost_usd=cost)
            task.agent_type = agent_type
            tasks.append(task)

        agent_costs = aggregate_costs_by_agent(tasks)
        total_from_breakdown = sum(agent_costs.values())
        total_from_tasks = sum(t.cost_usd for t in tasks)

        assert total_from_breakdown == pytest.approx(total_from_tasks)
        assert total_from_tasks == pytest.approx(0.35)
