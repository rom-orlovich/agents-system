import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from core.database.models import TaskDB, SessionDB


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalyticsAPI:
    """Integration tests for analytics endpoints."""
    
    async def test_analytics_summary_empty(self, client: AsyncClient):
        """Summary with no tasks returns zeros."""
        response = await client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["today_cost"] == 0.0
        assert data["today_tasks"] == 0
        assert data["total_cost"] == 0.0
        assert data["total_tasks"] == 0
    
    async def test_analytics_summary_with_tasks(self, client: AsyncClient, db_session):
        """Summary returns correct aggregated data."""
        # Create session
        session = SessionDB(session_id="test-sess", user_id="user-1", machine_id="m-1")
        db_session.add(session)
        await db_session.flush()
        
        # Create tasks for today
        today = datetime.utcnow()
        for i in range(3):
            task = TaskDB(
                task_id=f"today-task-{i}",
                session_id="test-sess",
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Today task {i}",
                cost_usd=0.10,
                created_at=today,
            )
            db_session.add(task)
        
        # Create tasks from yesterday
        yesterday = today - timedelta(days=1)
        for i in range(2):
            task = TaskDB(
                task_id=f"yesterday-task-{i}",
                session_id="test-sess",
                user_id="user-1",
                agent_type="executor",
                status="completed",
                input_message=f"Yesterday task {i}",
                cost_usd=0.05,
                created_at=yesterday,
            )
            db_session.add(task)
        await db_session.commit()
        
        response = await client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["today_cost"] == pytest.approx(0.30)  # 3 tasks * 0.10
        assert data["today_tasks"] == 3
        assert data["total_cost"] == pytest.approx(0.40)  # 3 * 0.10 + 2 * 0.05
        assert data["total_tasks"] == 5
    
    async def test_daily_costs_format(self, client: AsyncClient, db_session):
        """Daily costs returns correct format for Chart.js."""
        # Create session
        session = SessionDB(session_id="test-sess", user_id="user-1", machine_id="m-1")
        db_session.add(session)
        await db_session.flush()
        
        # Create tasks over several days
        base_date = datetime.utcnow()
        for day_offset in range(5):
            date = base_date - timedelta(days=day_offset)
            for i in range(2):
                task = TaskDB(
                    task_id=f"task-day{day_offset}-{i}",
                    session_id="test-sess",
                    user_id="user-1",
                    agent_type="planning",
                    status="completed",
                    input_message=f"Task {i}",
                    cost_usd=0.05,
                    created_at=date,
                )
                db_session.add(task)
        await db_session.commit()
        
        response = await client.get("/api/analytics/costs/daily?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "costs" in data
        assert "task_counts" in data
        assert isinstance(data["dates"], list)
        assert isinstance(data["costs"], list)
        assert isinstance(data["task_counts"], list)
        assert len(data["dates"]) == len(data["costs"])
        assert len(data["dates"]) == len(data["task_counts"])
    
    async def test_subagent_costs_format(self, client: AsyncClient, db_session):
        """Subagent costs returns correct format for Chart.js."""
        # Create session
        session = SessionDB(session_id="test-sess", user_id="user-1", machine_id="m-1")
        db_session.add(session)
        await db_session.flush()
        
        # Create tasks for different subagents
        subagents = ["planning", "executor", "code-review"]
        for subagent in subagents:
            for i in range(2):
                task = TaskDB(
                    task_id=f"{subagent}-task-{i}",
                    session_id="test-sess",
                    user_id="user-1",
                    assigned_agent=subagent,
                    agent_type="planning",
                    status="completed",
                    input_message=f"{subagent} task {i}",
                    cost_usd=0.10,
                )
                db_session.add(task)
        await db_session.commit()
        
        response = await client.get("/api/analytics/costs/by-subagent")
        assert response.status_code == 200
        data = response.json()
        assert "subagents" in data
        assert "costs" in data
        assert isinstance(data["subagents"], list)
        assert isinstance(data["costs"], list)
        assert len(data["subagents"]) == len(data["costs"])
        # Should have 3 subagents
        assert len(data["subagents"]) == 3
    
    async def test_daily_costs_empty(self, client: AsyncClient):
        """Daily costs with no data returns empty arrays."""
        response = await client.get("/api/analytics/costs/daily?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["dates"] == []
        assert data["costs"] == []
        assert data["task_counts"] == []
    
    async def test_subagent_costs_empty(self, client: AsyncClient):
        """Subagent costs with no data returns empty arrays."""
        response = await client.get("/api/analytics/costs/by-subagent")
        assert response.status_code == 200
        data = response.json()
        assert data["subagents"] == []
        assert data["costs"] == []
