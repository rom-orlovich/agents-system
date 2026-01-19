"""PostgreSQL database operations."""

from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from models import TaskStatus, TaskSource

Base = declarative_base()


class TaskDB(Base):
    """Task database model."""

    __tablename__ = "tasks"

    task_id = Column(String(100), primary_key=True)
    source = Column(SQLEnum(TaskSource), nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.QUEUED)

    # Input
    description = Column(Text, nullable=False)
    repository = Column(String(200))
    issue_key = Column(String(50))
    sentry_issue_id = Column(String(100))

    # Results (stored as JSON)
    discovery = Column(JSON)
    sentry_analysis = Column(JSON)
    plan = Column(JSON)
    execution = Column(JSON)

    # URLs
    plan_url = Column(String(500))
    pr_url = Column(String(500))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    approved_by = Column(String(100))
    completed_at = Column(DateTime)

    # Error tracking
    error = Column(Text)
    retry_count = Column(Integer, default=0)


class Database:
    """Database connection manager."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def save_task(self, task_data: dict) -> None:
        """Save or update task.

        Args:
            task_data: Task data dictionary
        """
        session = self.get_session()
        try:
            # Check if task exists
            task = session.query(TaskDB).filter_by(
                task_id=task_data["task_id"]
            ).first()

            if task:
                # Update existing task
                for key, value in task_data.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
            else:
                # Create new task
                task = TaskDB(**task_data)
                session.add(task)

            session.commit()
        finally:
            session.close()

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task data or None
        """
        session = self.get_session()
        try:
            task = session.query(TaskDB).filter_by(task_id=task_id).first()
            if task:
                return {
                    column.name: getattr(task, column.name)
                    for column in task.__table__.columns
                }
            return None
        finally:
            session.close()

    def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> list[dict]:
        """Get tasks with optional filters.

        Args:
            status: Filter by status
            limit: Maximum number of tasks

        Returns:
            List of task data
        """
        session = self.get_session()
        try:
            query = session.query(TaskDB)

            if status:
                query = query.filter_by(status=status)

            tasks = query.order_by(TaskDB.created_at.desc()).limit(limit).all()

            return [
                {
                    column.name: getattr(task, column.name)
                    for column in task.__table__.columns
                }
                for task in tasks
            ]
        finally:
            session.close()


# Global database instance
db = Database()
