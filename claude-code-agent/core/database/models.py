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


class WebhookConfigDB(Base):
    """Webhook configuration database model."""
    __tablename__ = "webhook_configs"
    
    webhook_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    endpoint = Column(String(500), nullable=False)
    secret = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    
    commands = relationship("WebhookCommandDB", back_populates="webhook", cascade="all, delete-orphan")
    events = relationship("WebhookEventDB", back_populates="webhook", cascade="all, delete-orphan")


class WebhookCommandDB(Base):
    """Webhook command database model."""
    __tablename__ = "webhook_commands"
    
    command_id = Column(String(255), primary_key=True)
    webhook_id = Column(String(255), ForeignKey("webhook_configs.webhook_id", ondelete="CASCADE"), nullable=False)
    trigger = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    agent = Column(String(255), nullable=True)
    template = Column(Text, nullable=False)
    conditions_json = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    
    webhook = relationship("WebhookConfigDB", back_populates="commands")


class WebhookEventDB(Base):
    """Webhook event log database model."""
    __tablename__ = "webhook_events"
    
    event_id = Column(String(255), primary_key=True)
    webhook_id = Column(String(255), ForeignKey("webhook_configs.webhook_id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload_json = Column(Text, nullable=False)
    matched_command = Column(String(255), nullable=True)
    task_id = Column(String(255), nullable=True)
    response_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    webhook = relationship("WebhookConfigDB", back_populates="events")


class ConversationDB(Base):
    """Conversation database model for managing chat history."""
    __tablename__ = "conversations"
    
    conversation_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)  # JSON for additional metadata
    
    # Relationships
    messages = relationship("ConversationMessageDB", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessageDB.created_at")


class ConversationMessageDB(Base):
    """Conversation message database model."""
    __tablename__ = "conversation_messages"
    
    message_id = Column(String(255), primary_key=True)
    conversation_id = Column(String(255), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    task_id = Column(String(255), nullable=True)  # Link to task if this message created a task
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)  # JSON for tokens, cost, etc.
    
    # Relationships
    conversation = relationship("ConversationDB", back_populates="messages")
