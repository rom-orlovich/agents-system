import pytest
import uuid
from httpx import AsyncClient
from datetime import datetime, timezone
from core.database.models import TaskDB, SessionDB


@pytest.mark.integration
class TestTaskTableAPI:
    """Integration tests for paginated task table."""
    
    async def test_task_table_empty(self, client: AsyncClient):
        """Empty database returns empty list with pagination info."""
        # Use a filter for a non-existent session to ensure empty results
        # This makes the test robust when run with other tests that create data
        unique_session = f"non-existent-session-{uuid.uuid4().hex[:8]}"
        response = await client.get(f"/api/tasks/table?session_id={unique_session}")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0
    
    async def test_task_table_pagination(self, client: AsyncClient, db_session):
        """Pagination returns correct page of results."""
        # Use unique session_id to avoid collisions
        unique_sess_id = f"test-sess-{uuid.uuid4().hex[:8]}"
        # Create session first
        session = SessionDB(session_id=unique_sess_id, user_id="user-1", machine_id="m-1", connected_at=datetime.now(timezone.utc))
        db_session.add(session)
        await db_session.flush()
        
        # Create 25 tasks
        for i in range(25):
            task = TaskDB(
                task_id=f"task-{i:03d}",
                session_id=unique_sess_id,
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Task {i}",
                cost_usd=0.01 * i,
            )
            db_session.add(task)
        await db_session.commit()
        
        # Page 1 (default page_size=20) - filter by session_id to avoid seeing other tests' data
        response = await client.get(f"/api/tasks/table?page=1&page_size=10&session_id={unique_sess_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["total_pages"] == 3
        
        # Page 3
        response = await client.get(f"/api/tasks/table?page=3&page_size=10&session_id={unique_sess_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 5  # Remaining tasks
        assert data["page"] == 3
    
    async def test_task_table_filter_by_status(self, client: AsyncClient, db_session):
        """Filter by status returns only matching tasks."""
        # Use unique session_id to avoid collisions
        unique_sess_id = f"test-sess-{uuid.uuid4().hex[:8]}"
        # Create session
        session = SessionDB(session_id=unique_sess_id, user_id="user-1", machine_id="m-1", connected_at=datetime.now(timezone.utc))
        db_session.add(session)
        await db_session.flush()
        
        # Create tasks with different statuses
        for i in range(5):
            task = TaskDB(
                task_id=f"completed-{i}",
                session_id=unique_sess_id,
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Completed task {i}",
            )
            db_session.add(task)
        
        for i in range(3):
            task = TaskDB(
                task_id=f"failed-{i}",
                session_id=unique_sess_id,
                user_id="user-1",
                agent_type="executor",
                status="failed",
                input_message=f"Failed task {i}",
            )
            db_session.add(task)
        await db_session.commit()
        
        # Filter by both status and session_id to avoid seeing other tests' data
        response = await client.get(f"/api/tasks/table?status=completed&session_id={unique_sess_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        for task in data["tasks"]:
            assert task["status"] == "completed"
    
    async def test_task_table_sort_by_cost(self, client: AsyncClient, db_session):
        """Sort by cost_usd works correctly."""
        # Use unique session_id to avoid collisions
        unique_sess_id = f"test-sess-{uuid.uuid4().hex[:8]}"
        # Create session
        session = SessionDB(session_id=unique_sess_id, user_id="user-1", machine_id="m-1", connected_at=datetime.now(timezone.utc))
        db_session.add(session)
        await db_session.flush()
        
        # Create tasks with different costs
        costs = [0.05, 0.02, 0.10, 0.01, 0.08]
        for i, cost in enumerate(costs):
            task = TaskDB(
                task_id=f"task-{i}",
                session_id=unique_sess_id,
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Task {i}",
                cost_usd=cost,
            )
            db_session.add(task)
        await db_session.commit()
        
        # Filter by session_id to avoid seeing other tests' data
        response = await client.get(f"/api/tasks/table?sort_by=cost_usd&sort_order=desc&session_id={unique_sess_id}")
        assert response.status_code == 200
        data = response.json()
        task_costs = [t["cost_usd"] for t in data["tasks"]]
        assert task_costs == sorted(task_costs, reverse=True)
    
    async def test_task_table_filter_by_session(self, client: AsyncClient, db_session):
        """Filter by session_id returns only tasks from that session."""
        # Create two sessions
        session1 = SessionDB(session_id="sess-1", user_id="user-1", machine_id="m-1")
        session2 = SessionDB(session_id="sess-2", user_id="user-1", machine_id="m-1")
        db_session.add(session1)
        db_session.add(session2)
        await db_session.flush()
        
        # Create tasks for session 1
        for i in range(3):
            task = TaskDB(
                task_id=f"sess1-task-{i}",
                session_id="sess-1",
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Session 1 task {i}",
            )
            db_session.add(task)
        
        # Create tasks for session 2
        for i in range(2):
            task = TaskDB(
                task_id=f"sess2-task-{i}",
                session_id="sess-2",
                user_id="user-1",
                agent_type="executor",
                status="completed",
                input_message=f"Session 2 task {i}",
            )
            db_session.add(task)
        await db_session.commit()
        
        response = await client.get("/api/tasks/table?session_id=sess-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        for task in data["tasks"]:
            assert task["session_id"] == "sess-1"
