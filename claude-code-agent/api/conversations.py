"""Conversation management API endpoints."""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from core.database import get_session as get_db_session
from core.database.models import ConversationDB, ConversationMessageDB, TaskDB
from shared import APIResponse

logger = structlog.get_logger()

router = APIRouter()


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
            content=msg.content,
            task_id=msg.task_id,
            created_at=msg.created_at.isoformat(),
            metadata=json.loads(msg.metadata_json) if msg.metadata_json else {},
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

    @classmethod
    def from_db(cls, conv: ConversationDB, message_count: int = 0) -> "ConversationResponse":
        """Create from database model."""
        return cls(
            conversation_id=conv.conversation_id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            is_archived=conv.is_archived,
            metadata=json.loads(conv.metadata_json) if conv.metadata_json else {},
            message_count=message_count,
        )


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation response with messages."""
    messages: List[MessageResponse]

    @classmethod
    def from_db_with_messages(cls, conv: ConversationDB) -> "ConversationDetailResponse":
        """Create from database model with messages."""
        return cls(
            conversation_id=conv.conversation_id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            is_archived=conv.is_archived,
            metadata=json.loads(conv.metadata_json) if conv.metadata_json else {},
            message_count=len(conv.messages),
            messages=[MessageResponse.from_db(msg) for msg in conv.messages],
        )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db_session)
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
    
    logger.info("conversation_created", conversation_id=conversation_id, user_id=data.user_id)
    
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
    query = select(ConversationDB).order_by(ConversationDB.updated_at.desc())
    
    if user_id:
        query = query.where(ConversationDB.user_id == user_id)
    
    if not include_archived:
        query = query.where(ConversationDB.is_archived == False)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Get message counts
    response_list = []
    for conv in conversations:
        count_query = select(func.count()).select_from(ConversationMessageDB).where(
            ConversationMessageDB.conversation_id == conv.conversation_id
        )
        count = (await db.execute(count_query)).scalar() or 0
        response_list.append(ConversationResponse.from_db(conv, message_count=count))
    
    return response_list


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
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
    
    if include_messages:
        # Eager load messages
        await db.refresh(conversation, ["messages"])
        return ConversationDetailResponse.from_db_with_messages(conversation)
    else:
        count_query = select(func.count()).select_from(ConversationMessageDB).where(
            ConversationMessageDB.conversation_id == conversation_id
        )
        count = (await db.execute(count_query)).scalar() or 0
        return ConversationDetailResponse(
            **ConversationResponse.from_db(conversation, message_count=count).dict(),
            messages=[]
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
    
    conversation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(conversation)
    
    logger.info("conversation_updated", conversation_id=conversation_id)
    
    count_query = select(func.count()).select_from(ConversationMessageDB).where(
        ConversationMessageDB.conversation_id == conversation_id
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
    
    return APIResponse(
        success=True,
        message="Conversation deleted successfully"
    )


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
    
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    
    logger.info("conversation_history_cleared", conversation_id=conversation_id, messages_deleted=len(messages))
    
    return APIResponse(
        success=True,
        message=f"Cleared {len(messages)} messages from conversation"
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
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
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(message)
    
    logger.info("message_added", conversation_id=conversation_id, message_id=message_id, role=data.role)
    
    return MessageResponse.from_db(message)


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
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
    
    query = select(ConversationMessageDB).where(
        ConversationMessageDB.conversation_id == conversation_id
    ).order_by(ConversationMessageDB.created_at.asc()).offset(offset).limit(limit)
    
    messages_result = await db.execute(query)
    messages = messages_result.scalars().all()
    
    return [MessageResponse.from_db(msg) for msg in messages]


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
    query = select(ConversationMessageDB).where(
        ConversationMessageDB.conversation_id == conversation_id
    ).order_by(ConversationMessageDB.created_at.desc()).limit(max_messages)
    
    messages_result = await db.execute(query)
    messages = list(reversed(messages_result.scalars().all()))  # Reverse to chronological order
    
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
        ]
    }
    
    return context
