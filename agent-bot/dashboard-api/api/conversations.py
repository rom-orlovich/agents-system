"""Conversation management API endpoints."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from core.database import get_session as get_db_session
from core.database.models import ConversationDB, ConversationMessageDB, TaskDB
from shared import APIResponse

logger = structlog.get_logger()

router = APIRouter()


def safe_json_loads(json_str: Optional[str]) -> dict:
    """Safely parse JSON string, returning empty dict on error."""
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(
            "Invalid JSON in metadata_json",
            error=str(e),
            json_str=json_str[:100] if json_str else None,
        )
        return {}


class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""

    title: str
    user_id: str = "default-user"
    metadata: dict = {}


class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""

    title: Optional[str] = None
    is_archived: Optional[bool] = None
    metadata: Optional[dict] = None


class MessageCreate(BaseModel):
    """Request model for creating a message."""

    role: str  # user, assistant, system
    content: str
    task_id: Optional[str] = None
    metadata: dict = {}


class MessageResponse(BaseModel):
    """Response model for a message."""

    message_id: str
    conversation_id: str
    role: str
    content: str
    task_id: Optional[str]
    created_at: str
    metadata: dict

    @classmethod
    def from_db(cls, msg: ConversationMessageDB) -> "MessageResponse":
        """Create from database model."""
        return cls(
            message_id=msg.message_id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content or "",
            task_id=msg.task_id,
            created_at=msg.created_at.isoformat()
            if msg.created_at
            else datetime.now(timezone.utc).isoformat(),
            metadata=safe_json_loads(msg.metadata_json),
        )


class ConversationResponse(BaseModel):
    """Response model for a conversation."""

    conversation_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    is_archived: bool
    metadata: dict
    message_count: int
    # Aggregated metrics
    total_cost_usd: float = 0.0
    total_tasks: int = 0
    total_duration_seconds: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_db(
        cls, conv: ConversationDB, message_count: int = 0
    ) -> "ConversationResponse":
        """Create from database model."""
        return cls(
            conversation_id=conv.conversation_id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            is_archived=conv.is_archived,
            metadata=safe_json_loads(conv.metadata_json),
            message_count=message_count,
            total_cost_usd=conv.total_cost_usd or 0.0,
            total_tasks=conv.total_tasks or 0,
            total_duration_seconds=conv.total_duration_seconds or 0.0,
            started_at=conv.started_at.isoformat() if conv.started_at else None,
            completed_at=conv.completed_at.isoformat() if conv.completed_at else None,
        )


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation response with messages."""

    messages: List[MessageResponse]

    @classmethod
    def from_db_with_messages(
        cls, conv: ConversationDB
    ) -> "ConversationDetailResponse":
        """Create from database model with messages."""
        return cls(
            conversation_id=conv.conversation_id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            is_archived=conv.is_archived,
            metadata=safe_json_loads(conv.metadata_json),
            message_count=len(conv.messages),
            messages=[MessageResponse.from_db(msg) for msg in conv.messages],
        )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate, db: AsyncSession = Depends(get_db_session)
):
    """Create a new conversation."""
    conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

    conversation = ConversationDB(
        conversation_id=conversation_id,
        user_id=data.user_id,
        title=data.title,
        metadata_json=json.dumps(data.metadata),
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    logger.info(
        "conversation_created", conversation_id=conversation_id, user_id=data.user_id
    )

    return ConversationResponse.from_db(conversation, message_count=0)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List conversations with optional filters."""
    try:
        query = select(ConversationDB).order_by(ConversationDB.updated_at.desc())

        if user_id:
            query = query.where(ConversationDB.user_id == user_id)

        if not include_archived:
            query = query.where(ConversationDB.is_archived.is_(False))

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        conversations = result.scalars().all()

        # Get message counts
        response_list = []
        for conv in conversations:
            try:
                count_query = (
                    select(func.count())
                    .select_from(ConversationMessageDB)
                    .where(
                        ConversationMessageDB.conversation_id == conv.conversation_id
                    )
                )
                count = (await db.execute(count_query)).scalar() or 0
                response_list.append(
                    ConversationResponse.from_db(conv, message_count=count)
                )
            except Exception as e:
                # Log error for individual conversation but continue processing others
                logger.error(
                    "Failed to process conversation",
                    conversation_id=conv.conversation_id,
                    error=str(e),
                    exc_info=True,
                )
                # Skip this conversation or add with empty metadata
                try:
                    response_list.append(
                        ConversationResponse.from_db(conv, message_count=0)
                    )
                except Exception:
                    # If even that fails, skip this conversation entirely
                    logger.warning(
                        "Skipping conversation due to processing error",
                        conversation_id=conv.conversation_id,
                    )

        return response_list
    except Exception as e:
        logger.error("Failed to list conversations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load conversations")


@router.get(
    "/conversations/{conversation_id}", response_model=ConversationDetailResponse
)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    include_messages: bool = Query(True),
):
    """Get a conversation by ID with optional messages."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        if include_messages:
            messages_query = (
                select(ConversationMessageDB)
                .where(ConversationMessageDB.conversation_id == conversation_id)
                .order_by(ConversationMessageDB.created_at.asc())
            )
            messages_result = await db.execute(messages_query)
            messages = messages_result.scalars().all()

            return ConversationDetailResponse(
                conversation_id=conversation.conversation_id,
                user_id=conversation.user_id,
                title=conversation.title,
                created_at=conversation.created_at.isoformat()
                if conversation.created_at
                else datetime.now(timezone.utc).isoformat(),
                updated_at=conversation.updated_at.isoformat()
                if conversation.updated_at
                else datetime.now(timezone.utc).isoformat(),
                is_archived=conversation.is_archived,
                metadata=safe_json_loads(conversation.metadata_json),
                message_count=len(messages),
                total_cost_usd=conversation.total_cost_usd or 0.0,
                total_tasks=conversation.total_tasks or 0,
                total_duration_seconds=conversation.total_duration_seconds or 0.0,
                started_at=conversation.started_at.isoformat()
                if conversation.started_at
                else None,
                completed_at=conversation.completed_at.isoformat()
                if conversation.completed_at
                else None,
                messages=[MessageResponse.from_db(msg) for msg in messages],
            )
        else:
            count_query = (
                select(func.count())
                .select_from(ConversationMessageDB)
                .where(ConversationMessageDB.conversation_id == conversation_id)
            )
            count = (await db.execute(count_query)).scalar() or 0
            return ConversationDetailResponse(
                **ConversationResponse.from_db(
                    conversation, message_count=count
                ).dict(),
                messages=[],
            )
    except Exception as e:
        logger.error(
            "Failed to get conversation",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to load conversation: {str(e)}"
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a conversation."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if data.title is not None:
        conversation.title = data.title

    if data.is_archived is not None:
        conversation.is_archived = data.is_archived

    if data.metadata is not None:
        conversation.metadata_json = json.dumps(data.metadata)

    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(conversation)

    logger.info("conversation_updated", conversation_id=conversation_id)

    count_query = (
        select(func.count())
        .select_from(ConversationMessageDB)
        .where(ConversationMessageDB.conversation_id == conversation_id)
    )
    count = (await db.execute(count_query)).scalar() or 0

    return ConversationResponse.from_db(conversation, message_count=count)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    logger.info("conversation_deleted", conversation_id=conversation_id)

    return APIResponse(success=True, message="Conversation deleted successfully")


@router.post("/conversations/{conversation_id}/clear")
async def clear_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Clear all messages in a conversation."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete all messages
    delete_query = select(ConversationMessageDB).where(
        ConversationMessageDB.conversation_id == conversation_id
    )
    messages_result = await db.execute(delete_query)
    messages = messages_result.scalars().all()

    for msg in messages:
        await db.delete(msg)

    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        "conversation_history_cleared",
        conversation_id=conversation_id,
        messages_deleted=len(messages),
    )

    return APIResponse(
        success=True, message=f"Cleared {len(messages)} messages from conversation"
    )


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageResponse
)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Add a message to a conversation."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_id = f"msg-{uuid.uuid4().hex[:12]}"

    message = ConversationMessageDB(
        message_id=message_id,
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
        task_id=data.task_id,
        metadata_json=json.dumps(data.metadata),
    )

    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(message)

    logger.info(
        "message_added",
        conversation_id=conversation_id,
        message_id=message_id,
        role=data.role,
    )

    return MessageResponse.from_db(message)


@router.get(
    "/conversations/{conversation_id}/messages", response_model=List[MessageResponse]
)
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get messages from a conversation."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    query = (
        select(ConversationMessageDB)
        .where(ConversationMessageDB.conversation_id == conversation_id)
        .order_by(ConversationMessageDB.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    messages_result = await db.execute(query)
    messages = messages_result.scalars().all()

    return [MessageResponse.from_db(msg) for msg in messages]


@router.get("/conversations/{conversation_id}/metrics")
async def get_conversation_metrics(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get aggregated metrics for a conversation."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get task breakdown by status
    task_breakdown_query = (
        select(TaskDB.status, func.count().label("count"))
        .where(TaskDB.source_metadata.like(f'%"conversation_id": "{conversation_id}"%'))
        .group_by(TaskDB.status)
    )

    breakdown_result = await db.execute(task_breakdown_query)
    breakdown_rows = breakdown_result.all()

    task_breakdown = {}
    for row in breakdown_rows:
        task_breakdown[row.status] = row.count

    # Calculate average cost per task
    average_cost_per_task = (
        conversation.total_cost_usd / conversation.total_tasks
        if conversation.total_tasks > 0
        else 0.0
    )

    metrics = {
        "conversation_id": conversation_id,
        "total_cost_usd": conversation.total_cost_usd or 0.0,
        "total_tasks": conversation.total_tasks or 0,
        "total_duration_seconds": conversation.total_duration_seconds or 0.0,
        "started_at": conversation.started_at.isoformat()
        if conversation.started_at
        else None,
        "completed_at": conversation.completed_at.isoformat()
        if conversation.completed_at
        else None,
        "task_breakdown": task_breakdown,
        "average_cost_per_task": round(average_cost_per_task, 4),
    }

    return metrics


@router.get("/conversations/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    max_messages: int = Query(20, ge=1, le=100),
):
    """Get conversation context for the agent (recent messages formatted for Claude)."""
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get recent messages
    query = (
        select(ConversationMessageDB)
        .where(ConversationMessageDB.conversation_id == conversation_id)
        .order_by(ConversationMessageDB.created_at.desc())
        .limit(max_messages)
    )

    messages_result = await db.execute(query)
    messages = list(
        reversed(messages_result.scalars().all())
    )  # Reverse to chronological order

    # Format for Claude
    context = {
        "conversation_id": conversation_id,
        "title": conversation.title,
        "message_count": len(messages),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }

    return context
