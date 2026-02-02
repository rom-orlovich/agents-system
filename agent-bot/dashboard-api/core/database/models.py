"""SQLAlchemy database models."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now():
    """Get current UTC datetime - helper function to avoid SQLAlchemy deprecation warnings.

    SQLAlchemy wraps callable defaults, and using lambda directly can trigger
    deprecation warnings. This function provides a clean callable that returns
    timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""

    pass


class SessionDB(Base):
    """Session database model."""

    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    machine_id = Column(String(255), nullable=False)
    connected_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    disconnected_at = Column(DateTime, nullable=True, index=True)
    total_cost_usd = Column(Float, default=0.0, nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)
    active = Column(
        Boolean, default=True, nullable=False
    )  # CLI access active (not rate limited)

    # Relationships
    tasks = relationship("TaskDB", back_populates="session")


class TaskDB(Base):
    """Task database model."""

    __tablename__ = "tasks"

    task_id = Column(String(255), primary_key=True)
    session_id = Column(
        String(255), ForeignKey("sessions.session_id"), nullable=False, index=True
    )
    user_id = Column(String(255), nullable=False, index=True)

    # Assignment
    assigned_agent = Column(String(255), nullable=True)
    agent_type = Column(String(50), nullable=False)

    # Status
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
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

    # Flow tracking
    initiated_task_id = Column(
        String(255), nullable=True
    )  # Root task that initiated this flow (self-reference for root tasks)
    flow_id = Column(
        String(255), nullable=True, index=True
    )  # Unique identifier for the entire task flow

    # Relationships
    session = relationship("SessionDB", back_populates="tasks")


class EntityDB(Base):
    """Dynamic entity storage (webhooks, agents, skills)."""

    __tablename__ = "entities"

    name = Column(String(255), primary_key=True)
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # webhook, agent, skill
    config = Column(Text, nullable=False)  # JSON serialized Pydantic model
    is_builtin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


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
    created_at = Column(DateTime, nullable=False)
    created_by = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=True)

    commands = relationship(
        "WebhookCommandDB", back_populates="webhook", cascade="all, delete-orphan"
    )
    events = relationship(
        "WebhookEventDB", back_populates="webhook", cascade="all, delete-orphan"
    )


class WebhookCommandDB(Base):
    """Webhook command database model."""

    __tablename__ = "webhook_commands"

    command_id = Column(String(255), primary_key=True)
    webhook_id = Column(
        String(255),
        ForeignKey("webhook_configs.webhook_id", ondelete="CASCADE"),
        nullable=False,
    )
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
    webhook_id = Column(
        String(255),
        ForeignKey("webhook_configs.webhook_id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String(50), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload_json = Column(Text, nullable=False)
    matched_command = Column(String(255), nullable=True)
    task_id = Column(String(255), nullable=True)
    response_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    webhook = relationship("WebhookConfigDB", back_populates="events")


class ConversationDB(Base):
    """Conversation database model for managing chat history."""

    __tablename__ = "conversations"

    conversation_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(
        Text, default="{}", nullable=False
    )  # JSON for additional metadata

    # Flow tracking
    initiated_task_id = Column(
        String(255), nullable=True
    )  # Root task that started this conversation
    flow_id = Column(
        String(255), nullable=True, index=True
    )  # Flow ID for end-to-end tracking

    # Aggregated metrics
    total_cost_usd = Column(Float, default=0.0, nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)
    total_duration_seconds = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime, nullable=True)  # Earliest task start time
    completed_at = Column(DateTime, nullable=True)  # Latest task completion time

    # Relationships
    messages = relationship(
        "ConversationMessageDB",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessageDB.created_at",
    )


class ConversationMessageDB(Base):
    """Conversation message database model."""

    __tablename__ = "conversation_messages"

    message_id = Column(String(255), primary_key=True)
    conversation_id = Column(
        String(255),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    task_id = Column(
        String(255), nullable=True
    )  # Link to task if this message created a task
    created_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(
        Text, default="{}", nullable=False
    )  # JSON for tokens, cost, etc.

    # Relationships
    conversation = relationship("ConversationDB", back_populates="messages")


class AccountDB(Base):
    """User account database model."""

    __tablename__ = "accounts"

    account_id = Column(String(255), primary_key=True)  # From credential user_id
    email = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    credential_status = Column(
        String(50), default="valid"
    )  # valid, expired, revoked, expiring_soon
    credential_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    metadata_json = Column(Text, default="{}")

    # Relationships
    machines = relationship("MachineDB", back_populates="account")


class MachineDB(Base):
    """Machine/container instance database model."""

    __tablename__ = "machines"

    machine_id = Column(String(255), primary_key=True)  # e.g., "claude-agent-001"
    account_id = Column(String(255), ForeignKey("accounts.account_id"), nullable=True)
    display_name = Column(String(255), nullable=True)
    status = Column(String(50), default="offline")  # online, offline, busy, error
    last_heartbeat = Column(DateTime, nullable=True)
    container_id = Column(String(255), nullable=True)  # Docker container ID
    host_info = Column(Text, default="{}")  # JSON: hostname, IP, resources
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    account = relationship("AccountDB", back_populates="machines")


class SubagentExecutionDB(Base):
    """Subagent execution tracking."""

    __tablename__ = "subagent_executions"

    execution_id = Column(String(255), primary_key=True)
    parent_task_id = Column(String(255), ForeignKey("tasks.task_id"), nullable=True)
    agent_name = Column(String(255), nullable=False)
    mode = Column(String(50), nullable=False)  # foreground, background, parallel
    status = Column(String(50), nullable=False)  # running, completed, failed, stopped
    permission_mode = Column(
        String(50), default="default"
    )  # default, auto-deny, acceptEdits
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    context_tokens = Column(Integer, default=0)
    result_summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # Parallel group tracking
    group_id = Column(String(255), nullable=True, index=True)


class SkillExecutionDB(Base):
    """Skill execution tracking."""

    __tablename__ = "skill_executions"

    execution_id = Column(String(255), primary_key=True)
    task_id = Column(String(255), ForeignKey("tasks.task_id"), nullable=True)
    skill_name = Column(String(255), nullable=False)
    input_params = Column(Text, default="{}")  # JSON
    output_result = Column(Text, nullable=True)  # JSON
    success = Column(Boolean, default=False)
    executed_at = Column(DateTime, default=utc_now)
    duration_seconds = Column(Float, default=0.0)


class AuditLogDB(Base):
    """Audit log for tracking sensitive actions."""

    __tablename__ = "audit_log"

    log_id = Column(String(255), primary_key=True)
    action = Column(
        String(100), nullable=False, index=True
    )  # webhook_create, subagent_spawn, etc.
    actor = Column(String(255), nullable=False)  # user_id or system
    target_type = Column(String(100), nullable=True)  # webhook, subagent, agent, skill
    target_id = Column(String(255), nullable=True)
    details_json = Column(Text, default="{}")  # JSON with action-specific details
    created_at = Column(DateTime, default=utc_now, index=True)


async def update_conversation_metrics(
    conversation_id: str, task: TaskDB, db: AsyncSession
) -> None:
    """
    Update conversation aggregated metrics when a task completes.

    Args:
        conversation_id: Conversation ID to update
        task: Completed task
        db: Database session
    """
    from sqlalchemy import select

    # Get conversation
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        return

    # Update aggregated metrics
    conversation.total_cost_usd += task.cost_usd or 0.0
    conversation.total_tasks += 1
    conversation.total_duration_seconds += task.duration_seconds or 0.0

    # Update started_at (earliest task start)
    if task.started_at:
        # Ensure timezone-aware comparison
        task_started = task.started_at
        if task_started.tzinfo is None:
            task_started = task_started.replace(tzinfo=timezone.utc)

        if conversation.started_at is None:
            conversation.started_at = task_started
        else:
            conv_started = conversation.started_at
            if conv_started.tzinfo is None:
                conv_started = conv_started.replace(tzinfo=timezone.utc)
            if task_started < conv_started:
                conversation.started_at = task_started

    # Update completed_at (latest task completion)
    if task.completed_at:
        # Ensure timezone-aware comparison
        task_completed = task.completed_at
        if task_completed.tzinfo is None:
            task_completed = task_completed.replace(tzinfo=timezone.utc)

        if conversation.completed_at is None:
            conversation.completed_at = task_completed
        else:
            conv_completed = conversation.completed_at
            if conv_completed.tzinfo is None:
                conv_completed = conv_completed.replace(tzinfo=timezone.utc)
            if task_completed > conv_completed:
                conversation.completed_at = task_completed

    # Update updated_at timestamp
    conversation.updated_at = datetime.now(timezone.utc)

    db.add(conversation)
