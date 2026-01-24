"""Subagent management API endpoints."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_session
from core.database.redis_client import redis_client
from core.database.models import SubagentExecutionDB, AuditLogDB

router = APIRouter(prefix="/api/v2/subagents", tags=["subagents"])

MAX_PARALLEL_SUBAGENTS = 10


class SpawnSubagentRequest(BaseModel):
    """Request to spawn a new subagent."""
    agent_type: str = Field(..., description="Type of agent: planning, executor, etc.")
    mode: str = Field(default="foreground", description="foreground, background, or parallel")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    prompt: Optional[str] = Field(None, description="Initial prompt for the subagent")


class SpawnSubagentResponse(BaseModel):
    """Response from spawning a subagent."""
    subagent_id: str
    agent_type: str
    mode: str
    permission_mode: str
    status: str


class ParallelSpawnRequest(BaseModel):
    """Request to spawn multiple subagents in parallel."""
    agents: List[dict] = Field(..., description="List of agent configs with type and task")


class SubagentStatus(BaseModel):
    """Subagent status information."""
    subagent_id: str
    agent_name: str
    mode: str
    status: str
    permission_mode: str
    started_at: Optional[str] = None


@router.post("/spawn", response_model=dict)
async def spawn_subagent(
    request: SpawnSubagentRequest,
    db: AsyncSession = Depends(get_session)
):
    """Spawn a new subagent."""
    # Check max parallel limit
    active_count = await redis_client.get_active_subagent_count()
    if active_count >= MAX_PARALLEL_SUBAGENTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum of {MAX_PARALLEL_SUBAGENTS} parallel subagents reached. Please wait for some to complete."
        )
    
    subagent_id = f"subagent-{uuid.uuid4().hex[:12]}"
    
    # Determine permission mode based on execution mode
    permission_mode = "auto-deny" if request.mode == "background" else "default"
    
    # Add to Redis active set
    await redis_client.add_active_subagent(subagent_id, {
        "status": "running",
        "mode": request.mode,
        "agent_name": request.agent_type,
        "permission_mode": permission_mode,
        "started_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Create database record
    execution = SubagentExecutionDB(
        execution_id=subagent_id,
        parent_task_id=request.task_id,
        agent_name=request.agent_type,
        mode=request.mode,
        status="running",
        permission_mode=permission_mode
    )
    db.add(execution)
    
    # Audit log
    audit = AuditLogDB(
        log_id=f"audit-{uuid.uuid4().hex[:12]}",
        action="subagent_spawn",
        actor="system",
        target_type="subagent",
        target_id=subagent_id,
        details_json=f'{{"agent_type": "{request.agent_type}", "mode": "{request.mode}"}}'
    )
    db.add(audit)
    
    await db.commit()
    
    return {
        "data": {
            "subagent_id": subagent_id,
            "agent_type": request.agent_type,
            "mode": request.mode,
            "permission_mode": permission_mode,
            "status": "running"
        }
    }


@router.get("/active", response_model=dict)
async def list_active_subagents():
    """List all active subagents."""
    active_ids = await redis_client.get_active_subagents()
    
    subagents = []
    for subagent_id in active_ids:
        status_data = await redis_client.get_subagent_status(subagent_id)
        if status_data:
            subagents.append({
                "subagent_id": subagent_id,
                **status_data
            })
    
    return {"data": subagents}


@router.get("/{subagent_id}", response_model=dict)
async def get_subagent(subagent_id: str):
    """Get subagent status."""
    status_data = await redis_client.get_subagent_status(subagent_id)
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subagent {subagent_id} not found"
        )
    
    return {
        "data": {
            "subagent_id": subagent_id,
            **status_data
        }
    }


@router.post("/{subagent_id}/stop", response_model=dict)
async def stop_subagent(
    subagent_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Stop a running subagent."""
    status_data = await redis_client.get_subagent_status(subagent_id)
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subagent {subagent_id} not found"
        )
    
    # Remove from active set
    await redis_client.remove_active_subagent(subagent_id)
    
    # Update database
    result = await db.execute(
        select(SubagentExecutionDB).where(SubagentExecutionDB.execution_id == subagent_id)
    )
    execution = result.scalar_one_or_none()
    if execution:
        execution.status = "stopped"
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()
    
    return {"data": {"subagent_id": subagent_id, "status": "stopped"}}


@router.get("/{subagent_id}/output", response_model=dict)
async def get_subagent_output(subagent_id: str):
    """Get subagent output stream."""
    output = await redis_client.get_subagent_output(subagent_id)
    status_data = await redis_client.get_subagent_status(subagent_id)
    
    if not status_data and not output:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subagent {subagent_id} not found"
        )
    
    return {
        "subagent_id": subagent_id,
        "output": output or "",
        "status": status_data.get("status", "unknown") if status_data else "unknown"
    }


@router.get("/{subagent_id}/context", response_model=dict)
async def get_subagent_context(
    subagent_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get subagent context information."""
    from core.database.models import ConversationMessageDB, SubagentExecutionDB
    
    # Get subagent execution record
    result = await db.execute(
        select(SubagentExecutionDB).where(SubagentExecutionDB.execution_id == subagent_id)
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subagent {subagent_id} not found"
        )
    
    # For now, return basic context info
    # In full implementation, this would fetch conversation messages
    return {
        "subagent_id": subagent_id,
        "message_count": 0,
        "context_tokens": execution.context_tokens or 0,
        "conversation_id": None
    }


@router.post("/parallel", response_model=dict)
async def spawn_parallel_subagents(
    request: ParallelSpawnRequest,
    db: AsyncSession = Depends(get_session)
):
    """Spawn multiple subagents in parallel."""
    # Check if we have capacity
    active_count = await redis_client.get_active_subagent_count()
    needed = len(request.agents)
    
    if active_count + needed > MAX_PARALLEL_SUBAGENTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Cannot spawn {needed} agents. Maximum is {MAX_PARALLEL_SUBAGENTS}, currently {active_count} active."
        )
    
    group_id = f"group-{uuid.uuid4().hex[:12]}"
    subagent_ids = []
    
    for agent_config in request.agents:
        subagent_id = f"subagent-{uuid.uuid4().hex[:12]}"
        subagent_ids.append(subagent_id)
        
        agent_type = agent_config.get("type", "planning")
        
        # Add to Redis
        await redis_client.add_active_subagent(subagent_id, {
            "status": "running",
            "mode": "parallel",
            "agent_name": agent_type,
            "permission_mode": "auto-deny",
            "started_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create database record
        execution = SubagentExecutionDB(
            execution_id=subagent_id,
            agent_name=agent_type,
            mode="parallel",
            status="running",
            permission_mode="auto-deny",
            group_id=group_id
        )
        db.add(execution)
    
    # Create parallel group in Redis
    await redis_client.create_parallel_group(group_id, subagent_ids)
    
    await db.commit()
    
    return {
        "data": {
            "group_id": group_id,
            "agent_count": len(subagent_ids),
            "subagent_ids": subagent_ids,
            "status": "running"
        }
    }


@router.get("/parallel/{group_id}/results", response_model=dict)
async def get_parallel_results(group_id: str):
    """Get results from a parallel execution group."""
    results = await redis_client.get_parallel_results(group_id)
    status_data = await redis_client.get_parallel_status(group_id)
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parallel group {group_id} not found"
        )
    
    # Format results
    formatted_results = [
        {"subagent_id": k, **v} for k, v in results.items()
    ]
    
    return {
        "group_id": group_id,
        "status": status_data.get("status", "unknown"),
        "total": int(status_data.get("total", 0)),
        "completed": int(status_data.get("completed", 0)),
        "results": formatted_results
    }
