import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from core.database.models import TaskDB, SessionDB
from api.analytics import get_analytics_summary

@pytest.mark.asyncio
async def test_analytics_summary_with_sqlite_datetime(db_session):
    """Test that analytics summary works correctly with SQLite datetime storage."""

    await db_session.execute(delete(TaskDB))
    await db_session.execute(delete(SessionDB))
    await db_session.commit()

    session = SessionDB(
        session_id="session-1",
        user_id="user-1",
        machine_id="machine-1",
        connected_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.flush()

    task = TaskDB(
        task_id="test-task-1",
        session_id="session-1",
        user_id="user-1",
        agent_type="planning",
        status="completed",
        input_message="test",
        cost_usd=1.5,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(task)
    await db_session.commit()

    summary = await get_analytics_summary(db=db_session)

    assert summary.today_cost == 1.5
    assert summary.today_tasks == 1
    assert summary.total_cost == 1.5
    assert summary.total_tasks == 1

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    task2 = TaskDB(
        task_id="test-task-2",
        session_id="session-1",
        user_id="user-1",
        agent_type="planning",
        status="completed",
        input_message="test yesterday",
        cost_usd=2.0,
        created_at=yesterday
    )
    db_session.add(task2)
    await db_session.commit()

    summary = await get_analytics_summary(db=db_session)

    assert summary.today_cost == 1.5
    assert summary.today_tasks == 1
    assert summary.total_cost == 3.5
    assert summary.total_tasks == 2
