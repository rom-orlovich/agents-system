"""Tests for conversation metrics aggregation (TDD Phase 0)."""

from datetime import datetime, timedelta, timezone
from core.database.models import TaskDB, ConversationDB, SessionDB
from shared import TaskStatus


class TestConversationMetrics:
    """Test conversation metrics aggregation."""
    async def test_conversation_total_cost_increases_on_task_completion(self, db):
        """Test: When task completes, conversation total_cost_usd increases."""
        from core.database.models import update_conversation_metrics
        
        # Create session
        session = SessionDB(
            session_id="session-metrics-1",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        # Create conversation
        conversation = ConversationDB(
            conversation_id="conv-metrics-1",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Create task
        task = TaskDB(
            task_id="task-metrics-1",
            session_id="session-metrics-1",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Test task",
            cost_usd=0.50,
            duration_seconds=10.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=10),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task)
        await db.flush()
        
        # Update conversation metrics
        await update_conversation_metrics(conversation.conversation_id, task, db)
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_cost_usd == 0.50
        assert conversation.total_tasks == 1
        assert conversation.total_duration_seconds == 10.0
    async def test_conversation_total_tasks_count_increases(self, db):
        """Test: When task completes, conversation total_tasks count increases."""
        from core.database.models import update_conversation_metrics
        
        session = SessionDB(
            session_id="session-metrics-2",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        conversation = ConversationDB(
            conversation_id="conv-metrics-2",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Complete first task
        task1 = TaskDB(
            task_id="task-metrics-2a",
            session_id="session-metrics-2",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Task 1",
            cost_usd=0.25,
            duration_seconds=5.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task1)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task1, db)
        
        # Complete second task
        task2 = TaskDB(
            task_id="task-metrics-2b",
            session_id="session-metrics-2",
            user_id="user-001",
            agent_type="executor",
            status=TaskStatus.COMPLETED,
            input_message="Task 2",
            cost_usd=0.30,
            duration_seconds=8.0,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=8),
            completed_at=datetime.now(timezone.utc)
        )
        db.add(task2)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task2, db)
        
        await db.commit()
        await db.refresh(conversation)
        
        assert conversation.total_tasks == 2
        assert conversation.total_cost_usd == 0.55  # 0.25 + 0.30
        assert conversation.total_duration_seconds == 13.0  # 5.0 + 8.0
    async def test_conversation_started_at_is_earliest_task_start(self, db):
        """Test: Conversation started_at is earliest task start time."""
        from core.database.models import update_conversation_metrics
        
        session = SessionDB(
            session_id="session-metrics-3",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        conversation = ConversationDB(
            conversation_id="conv-metrics-3",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # First task starts earlier
        task1_start = datetime.now(timezone.utc) - timedelta(minutes=10)
        task1 = TaskDB(
            task_id="task-metrics-3a",
            session_id="session-metrics-3",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Task 1",
            cost_usd=0.20,
            duration_seconds=5.0,
            started_at=task1_start,
            completed_at=task1_start + timedelta(seconds=5)
        )
        db.add(task1)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task1, db)
        
        # Second task starts later
        task2_start = datetime.now(timezone.utc) - timedelta(minutes=5)
        task2 = TaskDB(
            task_id="task-metrics-3b",
            session_id="session-metrics-3",
            user_id="user-001",
            agent_type="executor",
            status=TaskStatus.COMPLETED,
            input_message="Task 2",
            cost_usd=0.30,
            duration_seconds=8.0,
            started_at=task2_start,
            completed_at=task2_start + timedelta(seconds=8)
        )
        db.add(task2)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task2, db)
        
        await db.commit()
        await db.refresh(conversation)
        
        # started_at should be earliest (task1_start)
        assert conversation.started_at is not None
        # SQLite returns naive datetimes, convert to UTC-aware for comparison
        db_started_at = conversation.started_at
        if db_started_at.tzinfo is None:
            db_started_at = db_started_at.replace(tzinfo=timezone.utc)
        assert abs((db_started_at - task1_start).total_seconds()) < 1
    async def test_conversation_completed_at_is_latest_task_completion(self, db):
        """Test: Conversation completed_at is latest task completion time."""
        from core.database.models import update_conversation_metrics
        
        session = SessionDB(
            session_id="session-metrics-4",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        conversation = ConversationDB(
            conversation_id="conv-metrics-4",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # First task completes earlier
        task1_complete = datetime.now(timezone.utc) - timedelta(minutes=5)
        task1 = TaskDB(
            task_id="task-metrics-4a",
            session_id="session-metrics-4",
            user_id="user-001",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="Task 1",
            cost_usd=0.20,
            duration_seconds=5.0,
            started_at=task1_complete - timedelta(seconds=5),
            completed_at=task1_complete
        )
        db.add(task1)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task1, db)
        
        # Second task completes later
        task2_complete = datetime.now(timezone.utc)
        task2 = TaskDB(
            task_id="task-metrics-4b",
            session_id="session-metrics-4",
            user_id="user-001",
            agent_type="executor",
            status=TaskStatus.COMPLETED,
            input_message="Task 2",
            cost_usd=0.30,
            duration_seconds=8.0,
            started_at=task2_complete - timedelta(seconds=8),
            completed_at=task2_complete
        )
        db.add(task2)
        await db.flush()
        await update_conversation_metrics(conversation.conversation_id, task2, db)
        
        await db.commit()
        await db.refresh(conversation)
        
        # completed_at should be latest (task2_complete)
        assert conversation.completed_at is not None
        # SQLite returns naive datetimes, convert to UTC-aware for comparison
        db_completed_at = conversation.completed_at
        if db_completed_at.tzinfo is None:
            db_completed_at = db_completed_at.replace(tzinfo=timezone.utc)
        assert abs((db_completed_at - task2_complete).total_seconds()) < 1
    async def test_multiple_tasks_aggregate_metrics_correctly(self, db):
        """Test: Multiple tasks in conversation aggregate metrics correctly."""
        from core.database.models import update_conversation_metrics
        
        session = SessionDB(
            session_id="session-metrics-5",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        conversation = ConversationDB(
            conversation_id="conv-metrics-5",
            user_id="user-001",
            title="Test Conversation",
            total_cost_usd=0.0,
            total_tasks=0,
            total_duration_seconds=0.0
        )
        db.add(conversation)
        await db.flush()
        
        # Complete multiple tasks
        tasks = [
            TaskDB(
                task_id=f"task-metrics-5-{i}",
                session_id="session-metrics-5",
                user_id="user-001",
                agent_type="planning",
                status=TaskStatus.COMPLETED,
                input_message=f"Task {i}",
                cost_usd=0.10 * (i + 1),
                duration_seconds=5.0 * (i + 1),
                started_at=datetime.now(timezone.utc) - timedelta(seconds=5 * (i + 1)),
                completed_at=datetime.now(timezone.utc) - timedelta(seconds=5 * (i + 1)) + timedelta(seconds=5 * (i + 1))
            )
            for i in range(5)
        ]
        
        for task in tasks:
            db.add(task)
            await db.flush()
            await update_conversation_metrics(conversation.conversation_id, task, db)
        
        await db.commit()
        await db.refresh(conversation)
        
        # Verify aggregated metrics
        expected_cost = sum(0.10 * (i + 1) for i in range(5))  # 0.10 + 0.20 + 0.30 + 0.40 + 0.50 = 1.50
        expected_duration = sum(5.0 * (i + 1) for i in range(5))  # 5 + 10 + 15 + 20 + 25 = 75
        
        assert conversation.total_tasks == 5
        assert abs(conversation.total_cost_usd - expected_cost) < 0.01
        assert abs(conversation.total_duration_seconds - expected_duration) < 0.1
