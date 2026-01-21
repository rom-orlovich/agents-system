"""
Dashboard API endpoints for monitoring tasks and agents.
"""

import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus, TaskSource
from task_queue import RedisQueue

# Import agent registry
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.core.agent_registry import agent_registry

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
queue = RedisQueue()


@router.get("/agents")
async def get_agents():
    """
    Get all registered agents with metadata.

    Returns:
        Dict with list of agents and their metadata
    """
    agents = agent_registry.list_agents()

    return {
        "agents": [
            {
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "capabilities": [c.value for c in a.capabilities],
                "version": a.version,
                "enabled": a.enabled,
                "max_retries": a.max_retries,
                "timeout_seconds": a.timeout_seconds,
            }
            for a in agents
        ],
        "stats": agent_registry.get_stats()
    }


@router.get("/tasks")
async def get_tasks(
    agent: Optional[str] = Query(None, description="Filter by agent name"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    source: Optional[TaskSource] = Query(None, description="Filter by source"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(default=50, le=500, description="Maximum number of tasks")
):
    """
    Get tasks with filtering.

    Args:
        agent: Filter by agent name
        status: Filter by task status
        source: Filter by task source
        start_date: Filter tasks after this date
        end_date: Filter tasks before this date
        limit: Maximum number of tasks to return

    Returns:
        Dict with list of tasks
    """
    # TODO: Implement actual filtering in RedisQueue
    # For now, return placeholder

    return {
        "tasks": [],
        "total": 0,
        "filters": {
            "agent": agent,
            "status": status.value if status else None,
            "source": source.value if source else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "limit": limit
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    Get detailed information about a specific task.

    Args:
        task_id: Task identifier

    Returns:
        Task details including agent execution history
    """
    task = await queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get agent execution history for this task
    execution_history = agent_registry.get_execution_history(task_id=task_id)

    return {
        "task": task,
        "agent_executions": execution_history
    }


@router.get("/agent-stats")
async def get_agent_stats(
    agent: Optional[str] = Query(None, description="Filter by agent name")
):
    """
    Get agent execution statistics.

    Args:
        agent: Optional agent name to filter by

    Returns:
        Dict with agent statistics
    """
    if agent:
        execution_history = agent_registry.get_execution_history(agent_name=agent, limit=1000)
    else:
        execution_history = agent_registry.get_execution_history(limit=1000)

    # Calculate statistics
    total_executions = len(execution_history)
    successful = sum(1 for h in execution_history if h["success"])
    failed = total_executions - successful

    total_cost = sum(h["usage"]["total_cost_usd"] for h in execution_history)
    total_tokens = sum(h["usage"]["total_tokens"] for h in execution_history)
    avg_duration = (
        sum(h["duration_seconds"] for h in execution_history) / total_executions
        if total_executions > 0
        else 0
    )

    return {
        "agent": agent or "all",
        "total_executions": total_executions,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total_executions if total_executions > 0 else 0,
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "avg_duration_seconds": avg_duration,
    }


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    agent: Optional[str] = Query(None, description="Filter by agent name"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    group_by: str = Query(default="agent", regex="^(agent|day|task_type)$", description="Group by field")
):
    """
    Get cost breakdown with grouping.

    Args:
        agent: Optional agent name filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        group_by: Grouping field (agent, day, task_type)

    Returns:
        Dict with cost breakdown
    """
    # Get execution history
    if agent:
        execution_history = agent_registry.get_execution_history(agent_name=agent, limit=10000)
    else:
        execution_history = agent_registry.get_execution_history(limit=10000)

    # Filter by date range
    if start_date:
        execution_history = [
            h for h in execution_history
            if datetime.fromisoformat(h["timestamp"]) >= start_date
        ]
    if end_date:
        execution_history = [
            h for h in execution_history
            if datetime.fromisoformat(h["timestamp"]) <= end_date
        ]

    # Group by requested field
    cost_groups = {}

    for h in execution_history:
        if group_by == "agent":
            key = h["agent_name"]
        elif group_by == "day":
            date = datetime.fromisoformat(h["timestamp"]).date().isoformat()
            key = date
        elif group_by == "task_type":
            # Extract task type from task_id
            task_id = h["task_id"]
            parts = task_id.split("_")
            key = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else "unknown"
        else:
            key = "unknown"

        if key not in cost_groups:
            cost_groups[key] = {
                "name": key,
                "cost": 0,
                "count": 0,
                "tokens": 0
            }

        cost_groups[key]["cost"] += h["usage"]["total_cost_usd"]
        cost_groups[key]["count"] += 1
        cost_groups[key]["tokens"] += h["usage"]["total_tokens"]

    # Convert to list and sort by cost
    costs = list(cost_groups.values())
    costs.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "group_by": group_by,
        "costs": costs,
        "total_cost": sum(c["cost"] for c in costs),
        "total_executions": sum(c["count"] for c in costs),
    }


@router.get("/agent-chain-analytics")
async def get_agent_chain_analytics():
    """
    Get analytics on agent execution chains.

    Returns:
        Dict with agent chain patterns and statistics
    """
    execution_history = agent_registry.get_execution_history(limit=1000)

    # Group by task_id to get chains
    task_chains = {}
    for h in execution_history:
        task_id = h["task_id"]
        if task_id not in task_chains:
            task_chains[task_id] = []
        task_chains[task_id].append(h)

    # Analyze chain patterns
    chain_patterns = {}
    for task_id, executions in task_chains.items():
        # Sort by timestamp
        executions.sort(key=lambda x: x["timestamp"])

        # Create chain pattern
        chain = [e["agent_name"] for e in executions]
        pattern = " → ".join(chain)

        if pattern not in chain_patterns:
            chain_patterns[pattern] = {
                "pattern": pattern,
                "count": 0,
                "total_duration": 0,
                "total_cost": 0,
                "success_count": 0,
            }

        chain_patterns[pattern]["count"] += 1

        # Calculate totals
        total_duration = sum(e["duration_seconds"] for e in executions)
        total_cost = sum(e["usage"]["total_cost_usd"] for e in executions)
        all_successful = all(e["success"] for e in executions)

        chain_patterns[pattern]["total_duration"] += total_duration
        chain_patterns[pattern]["total_cost"] += total_cost
        if all_successful:
            chain_patterns[pattern]["success_count"] += 1

    # Convert to list and calculate averages
    patterns = list(chain_patterns.values())
    for p in patterns:
        count = p["count"]
        p["avg_duration"] = p["total_duration"] / count if count > 0 else 0
        p["avg_cost"] = p["total_cost"] / count if count > 0 else 0
        p["success_rate"] = p["success_count"] / count if count > 0 else 0

    # Sort by count
    patterns.sort(key=lambda x: x["count"], reverse=True)

    return {
        "chain_patterns": patterns,
        "total_chains": len(task_chains),
        "unique_patterns": len(patterns),
    }


@router.get("/metrics-summary")
async def get_metrics_summary():
    """
    Get summary metrics for dashboard overview.

    Returns:
        Dict with key metrics
    """
    # Get last 30 days of data
    start_date = datetime.now() - timedelta(days=30)
    execution_history = agent_registry.get_execution_history(limit=10000)

    # Filter last 30 days
    recent_history = [
        h for h in execution_history
        if datetime.fromisoformat(h["timestamp"]) >= start_date
    ]

    total_tasks = len(recent_history)
    successful = sum(1 for h in recent_history if h["success"])
    failed = total_tasks - successful
    total_cost = sum(h["usage"]["total_cost_usd"] for h in recent_history)
    avg_duration = (
        sum(h["duration_seconds"] for h in recent_history) / total_tasks
        if total_tasks > 0
        else 0
    )

    # Agent breakdown
    agent_counts = {}
    for h in recent_history:
        agent = h["agent_name"]
        if agent not in agent_counts:
            agent_counts[agent] = 0
        agent_counts[agent] += 1

    return {
        "period": "last_30_days",
        "total_tasks": total_tasks,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total_tasks if total_tasks > 0 else 0,
        "total_cost_usd": total_cost,
        "avg_duration_seconds": avg_duration,
        "agent_breakdown": agent_counts,
    }
