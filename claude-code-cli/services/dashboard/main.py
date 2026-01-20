import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import settings
from shared.task_queue import RedisQueue
from shared.models import TaskStatus, TaskSource
from shared.database import init_db, SessionLocal, TaskDB

app = FastAPI(title="AI Agent Dashboard")
queue = RedisQueue()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await queue.connect()
    # Initialize DB tables
    init_db()

@app.get("/api/tasks")
async def get_tasks(account_id: Optional[str] = None):
    """Get all tasks for the dashboard, optionally filtered by account_id."""
    # Get Redis tasks (active/recent)
    try:
        redis_tasks_list = await queue.get_all_tasks()
    except Exception as e:
        print(f"Redis error: {e}")
        redis_tasks_list = []
        
    redis_ids = {t.get("task_id") for t in redis_tasks_list}
    
    # Get DB tasks (history)
    db = SessionLocal()
    try:
        db_tasks = db.query(TaskDB).all()
        
        # Convert DB tasks to dicts and merge
        # Prefer Redis version if exists (more up to date for active tasks)
        merged_tasks = []
        
        # Add all Redis tasks first
        merged_tasks.extend(redis_tasks_list)
        
        # Add DB tasks that aren't in Redis
        for db_task in db_tasks:
            if db_task.task_id not in redis_ids:
                # Convert SQLAlchemy model to dict
                task_dict = {
                    "task_id": db_task.task_id,
                    "source": db_task.source,
                    "status": db_task.status,
                    "queued_at": db_task.queued_at.isoformat() if db_task.queued_at else None,
                    "updated_at": db_task.updated_at.isoformat() if db_task.updated_at else None,
                    "completed_at": db_task.completed_at.isoformat() if db_task.completed_at else None,
                    "cost_usd": db_task.cost_usd,
                    "input_tokens": db_task.input_tokens,
                    "output_tokens": db_task.output_tokens,
                    "error": db_task.error,
                    "repository": db_task.repository,
                    "pr_url": db_task.pr_url,
                    "issue_key": db_task.issue_key,
                    "account_id": db_task.account_id or "unknown"
                }
                # Merge with full JSON data if available
                if db_task.data:
                    task_dict.update(db_task.data)
                    # Ensure primary fields override JSON data which might be stale
                    task_dict["status"] = db_task.status
                    task_dict["cost_usd"] = db_task.cost_usd
                    # Ensure account_id from column takes precedence if set
                    if db_task.account_id and db_task.account_id != "unknown":
                         task_dict["account_id"] = db_task.account_id
                
                # Final safeguard
                if not task_dict.get("account_id"):
                    task_dict["account_id"] = "unknown"
                
                merged_tasks.append(task_dict)
                
    except Exception as e:
        print(f"DB Error: {e}")
        merged_tasks = redis_tasks_list
    finally:
        db.close()
        
    # Filter by account_id if provided
    if account_id:
        merged_tasks = [t for t in merged_tasks if t.get("account_id") == account_id]
        
    # Sort by updated_at or queued_at descending
    return sorted(merged_tasks, key=lambda x: x.get("updated_at") or x.get("queued_at") or "", reverse=True)

@app.get("/api/stats")
async def get_stats(account_id: Optional[str] = None):
    """Get aggregated stats."""
    # Get all tasks first to calculate available accounts
    all_tasks = await get_tasks(account_id=None)
    
    # Per-account/session stats (calculated from all tasks)
    account_stats = {}
    
    for task in all_tasks:
        acc_id = task.get("account_id") or "unknown"
        # Try to find email in task data
        email = task.get("email") or task.get("user_email") or task.get("user", {}).get("email")
        
        if acc_id not in account_stats:
            account_stats[acc_id] = {
                "account_id": acc_id,
                "email": email, # Store email if found
                "tasks": 0,
                "cost_usd": 0.0,
                "tokens": 0,
                "status_counts": {}
            }
        
        acc = account_stats[acc_id]
        # Update email if we found one and didn't have it before
        if email and not acc["email"]:
            acc["email"] = email
            
        acc["tasks"] += 1
        acc["cost_usd"] += float(task.get("cost_usd", 0))
        input_t = int(task.get("input_tokens", 0))
        output_t = int(task.get("output_tokens", 0))
        cache_r = int(task.get("cache_read_tokens", 0))
        acc["tokens"] += (input_t + output_t + cache_r)
        
        status = task.get("status", "unknown")
        acc["status_counts"][status] = acc["status_counts"].get(status, 0) + 1

    # If account_id filter is active, filter the tasks for the aggregation
    tasks_to_aggregate = all_tasks
    if account_id:
        tasks_to_aggregate = [t for t in all_tasks if t.get("account_id") == account_id]

    total_cost = 0.0
    total_tokens = 0
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_tasks = len(tasks_to_aggregate)
    status_counts = {}
    
    # Session tracking (e.g., last 24h)
    session_start = datetime.utcnow() - timedelta(hours=24)
    session_cost = 0.0
    session_tasks = 0
    
    for task in tasks_to_aggregate:
        # Metrics
        cost = float(task.get("cost_usd", 0))
        total_cost += cost
        
        input_t = int(task.get("input_tokens", 0))
        output_t = int(task.get("output_tokens", 0))
        cache_r = int(task.get("cache_read_tokens", 0))
        
        total_input += input_t
        total_output += output_t
        total_cache_read += cache_r
        total_tokens += (input_t + output_t + cache_r)
        
        # Status
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Session stats (Time-based global session)
        updated_at = task.get("updated_at")
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if dt.replace(tzinfo=None) > session_start:
                    session_cost += cost
                    session_tasks += 1
            except:
                pass

    # Determine session status
    active_tasks = [t for t in tasks_to_aggregate if t.get("status") in TaskStatus.active_states()]
    session_status = "active" if active_tasks else "idle"

    return {
        "total": {
            "cost_usd": total_cost,
            "tokens": total_tokens,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cache_read_tokens": total_cache_read,
            "tasks": total_tasks,
        },
        "session": {
            "status": session_status,
            "cost_usd": session_cost,
            "tasks": session_tasks,
            "limit_usd": settings.MAX_BUDGET_USD,
            "usage_percent": (session_cost / settings.MAX_BUDGET_USD * 100) if settings.MAX_BUDGET_USD > 0 else 0
        },
        "status_distribution": status_counts,
        "accounts": list(account_stats.values())
    }

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>Dashboard Coming Soon</h1>"

# Mount static files if directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
