"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""
    pass


class SessionDB(Base):
    """Session database model."""
    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    machine_id = Column(String(255), nullable=False)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    disconnected_at = Column(DateTime, nullable=True)
    total_cost_usd = Column(Float, default=0.0, nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)

    # Relationships
    tasks = relationship("TaskDB", back_populates="session")


class TaskDB(Base):
    """Task database model."""
    __tablename__ = "tasks"

    task_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Assignment
    assigned_agent = Column(String(255), nullable=True)
    agent_type = Column(String(50), nullable=False)

    # Status
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Input/Output
    input_message = Column(Text, nullable=False)
    output_stream = Column(Text, default="", nullable=False)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # Metrics
    cost_usd = Column(Float, default=0.0, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Float, default=0.0, nullable=False)

    # Metadata
    source = Column(String(50), default="dashboard", nullable=False)
    source_metadata = Column(Text, default="{}", nullable=False)  # JSON
    parent_task_id = Column(String(255), nullable=True)

    # Relationships
    session = relationship("SessionDB", back_populates="tasks")


class EntityDB(Base):
    """Dynamic entity storage (webhooks, agents, skills)."""
    __tablename__ = "entities"

    name = Column(String(255), primary_key=True)
    entity_type = Column(String(50), nullable=False, index=True)  # webhook, agent, skill
    config = Column(Text, nullable=False)  # JSON serialized Pydantic model
    is_builtin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
