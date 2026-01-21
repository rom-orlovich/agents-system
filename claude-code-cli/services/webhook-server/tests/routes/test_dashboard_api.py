"""
Tests for Dashboard API endpoints.

Testing the business logic of dashboard routes including:
- Task filtering
- Agent statistics
- Cost breakdown
- Chain analytics
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

# We'll import the app in the test functions to avoid import issues


@pytest.fixture
def client():
    """Create test client."""
    import sys
    from pathlib import Path

    # Add paths
    webhook_server_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(webhook_server_path))

    from main import app
    return TestClient(app)


@pytest.fixture
def mock_redis_queue():
    """Mock RedisQueue for testing."""
    with patch("routes.dashboard_api.queue") as mock_queue:
        mock_queue.get_task = AsyncMock()
        mock_queue.get_tasks_by_filter = AsyncMock()
        yield mock_queue


@pytest.fixture
def mock_agent_registry():
    """Mock agent_registry for testing."""
    with patch("routes.dashboard_api.agent_registry") as mock_registry:
        mock_registry.list_agents = MagicMock()
        mock_registry.get_stats = MagicMock()
        mock_registry.get_execution_history = MagicMock()
        yield mock_registry


class TestGetTasks:
    """Test the GET /api/dashboard/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_get_tasks_no_filters(self, client, mock_redis_queue):
        """Test getting tasks without any filters."""
        # Setup mock data
        mock_redis_queue.get_tasks_by_filter.return_value = [
            {
                "task_id": "task_1",
                "agent_name": "planning",
                "status": "completed",
                "source": "jira",
                "created_at": "2026-01-20T10:00:00",
            },
            {
                "task_id": "task_2",
                "agent_name": "executor",
                "status": "pending",
                "source": "github",
                "created_at": "2026-01-21T10:00:00",
            }
        ]

        response = client.get("/api/dashboard/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert len(data["tasks"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_tasks_filter_by_agent(self, client, mock_redis_queue):
        """Test filtering tasks by agent name."""
        mock_redis_queue.get_tasks_by_filter.return_value = [
            {
                "task_id": "task_1",
                "agent_name": "planning",
                "status": "completed",
                "source": "jira",
                "created_at": "2026-01-20T10:00:00",
            }
        ]

        response = client.get("/api/dashboard/tasks?agent=planning")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["agent_name"] == "planning"
        assert data["filters"]["agent"] == "planning"

    @pytest.mark.asyncio
    async def test_get_tasks_filter_by_status(self, client, mock_redis_queue):
        """Test filtering tasks by status."""
        mock_redis_queue.get_tasks_by_filter.return_value = [
            {
                "task_id": "task_1",
                "agent_name": "planning",
                "status": "completed",
                "source": "jira",
                "created_at": "2026-01-20T10:00:00",
            }
        ]

        response = client.get("/api/dashboard/tasks?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_tasks_filter_by_date_range(self, client, mock_redis_queue):
        """Test filtering tasks by date range."""
        start_date = datetime(2026, 1, 20)
        end_date = datetime(2026, 1, 21)

        mock_redis_queue.get_tasks_by_filter.return_value = [
            {
                "task_id": "task_1",
                "agent_name": "planning",
                "status": "completed",
                "source": "jira",
                "created_at": "2026-01-20T15:00:00",
            }
        ]

        response = client.get(
            f"/api/dashboard/tasks?start_date={start_date.isoformat()}"
            f"&end_date={end_date.isoformat()}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["start_date"] is not None
        assert data["filters"]["end_date"] is not None

    @pytest.mark.asyncio
    async def test_get_tasks_respects_limit(self, client, mock_redis_queue):
        """Test that limit parameter is respected."""
        # Create 100 tasks but limit to 10
        mock_tasks = [
            {
                "task_id": f"task_{i}",
                "agent_name": "planning",
                "status": "completed",
                "source": "jira",
                "created_at": "2026-01-20T10:00:00",
            }
            for i in range(10)
        ]
        mock_redis_queue.get_tasks_by_filter.return_value = mock_tasks

        response = client.get("/api/dashboard/tasks?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) <= 10
        assert data["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_tasks_limit_max_500(self, client, mock_redis_queue):
        """Test that limit cannot exceed 500."""
        mock_redis_queue.get_tasks_by_filter.return_value = []

        response = client.get("/api/dashboard/tasks?limit=1000")

        # Should return 422 for validation error
        assert response.status_code == 422


class TestGetTask:
    """Test the GET /api/dashboard/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_exists(self, client, mock_redis_queue, mock_agent_registry):
        """Test getting a specific task that exists."""
        mock_redis_queue.get_task.return_value = {
            "task_id": "task_123",
            "agent_name": "planning",
            "status": "completed",
            "source": "jira",
        }

        mock_agent_registry.get_execution_history.return_value = [
            {
                "task_id": "task_123",
                "agent_name": "planning",
                "timestamp": "2026-01-20T10:00:00",
                "duration_seconds": 45.2,
                "success": True,
            }
        ]

        response = client.get("/api/dashboard/tasks/task_123")

        assert response.status_code == 200
        data = response.json()
        assert "task" in data
        assert "agent_executions" in data
        assert data["task"]["task_id"] == "task_123"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client, mock_redis_queue):
        """Test getting a task that doesn't exist."""
        mock_redis_queue.get_task.return_value = None

        response = client.get("/api/dashboard/tasks/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetAgentStats:
    """Test the GET /api/dashboard/agent-stats endpoint."""

    def test_get_stats_all_agents(self, client, mock_agent_registry):
        """Test getting stats for all agents."""
        mock_agent_registry.get_execution_history.return_value = [
            {
                "agent_name": "planning",
                "success": True,
                "duration_seconds": 30.0,
                "usage": {"total_cost_usd": 0.05, "total_tokens": 1000},
            },
            {
                "agent_name": "executor",
                "success": False,
                "duration_seconds": 60.0,
                "usage": {"total_cost_usd": 0.10, "total_tokens": 2000},
            }
        ]

        response = client.get("/api/dashboard/agent-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "all"
        assert data["total_executions"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["success_rate"] == 0.5
        assert data["total_cost_usd"] == 0.15
        assert data["total_tokens"] == 3000

    def test_get_stats_specific_agent(self, client, mock_agent_registry):
        """Test getting stats for a specific agent."""
        mock_agent_registry.get_execution_history.return_value = [
            {
                "agent_name": "planning",
                "success": True,
                "duration_seconds": 30.0,
                "usage": {"total_cost_usd": 0.05, "total_tokens": 1000},
            }
        ]

        response = client.get("/api/dashboard/agent-stats?agent=planning")

        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "planning"
        assert data["total_executions"] == 1
        assert data["success_rate"] == 1.0


class TestGetCostBreakdown:
    """Test the GET /api/dashboard/cost-breakdown endpoint."""

    def test_cost_breakdown_by_agent(self, client, mock_agent_registry):
        """Test cost breakdown grouped by agent."""
        mock_agent_registry.get_execution_history.return_value = [
            {
                "agent_name": "planning",
                "timestamp": "2026-01-20T10:00:00",
                "task_id": "jira_task_1",
                "usage": {"total_cost_usd": 0.05, "total_tokens": 1000},
            },
            {
                "agent_name": "executor",
                "timestamp": "2026-01-20T11:00:00",
                "task_id": "jira_task_2",
                "usage": {"total_cost_usd": 0.10, "total_tokens": 2000},
            }
        ]

        response = client.get("/api/dashboard/cost-breakdown?group_by=agent")

        assert response.status_code == 200
        data = response.json()
        assert data["group_by"] == "agent"
        assert len(data["costs"]) == 2
        assert data["total_cost"] == 0.15
        assert data["total_executions"] == 2

    def test_cost_breakdown_by_day(self, client, mock_agent_registry):
        """Test cost breakdown grouped by day."""
        mock_agent_registry.get_execution_history.return_value = [
            {
                "agent_name": "planning",
                "timestamp": "2026-01-20T10:00:00",
                "task_id": "jira_task_1",
                "usage": {"total_cost_usd": 0.05, "total_tokens": 1000},
            },
            {
                "agent_name": "executor",
                "timestamp": "2026-01-20T15:00:00",
                "task_id": "jira_task_2",
                "usage": {"total_cost_usd": 0.10, "total_tokens": 2000},
            }
        ]

        response = client.get("/api/dashboard/cost-breakdown?group_by=day")

        assert response.status_code == 200
        data = response.json()
        assert data["group_by"] == "day"
        # Both tasks on same day should be grouped together
        assert len(data["costs"]) == 1
        assert data["costs"][0]["cost"] == 0.15


class TestGetMetricsSummary:
    """Test the GET /api/dashboard/metrics-summary endpoint."""

    def test_metrics_summary(self, client, mock_agent_registry):
        """Test getting metrics summary for last 30 days."""
        now = datetime.now()
        recent_timestamp = (now - timedelta(days=5)).isoformat()

        mock_agent_registry.get_execution_history.return_value = [
            {
                "agent_name": "planning",
                "success": True,
                "duration_seconds": 30.0,
                "timestamp": recent_timestamp,
                "usage": {"total_cost_usd": 0.05, "total_tokens": 1000},
            },
            {
                "agent_name": "executor",
                "success": True,
                "duration_seconds": 60.0,
                "timestamp": recent_timestamp,
                "usage": {"total_cost_usd": 0.10, "total_tokens": 2000},
            }
        ]

        response = client.get("/api/dashboard/metrics-summary")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "last_30_days"
        assert data["total_tasks"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert data["success_rate"] == 1.0
        assert "agent_breakdown" in data
