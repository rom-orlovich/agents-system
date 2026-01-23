"""Claude Code Tasks sync functionality for background agent visibility."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import structlog

from core.config import settings
from core.database.models import TaskDB
from shared import TaskStatus

logger = structlog.get_logger()


def get_claude_tasks_directory() -> Path:
    """Get Claude Code Tasks directory path."""
    if settings.claude_tasks_directory:
        return Path(settings.claude_tasks_directory)
    return Path.home() / ".claude" / "tasks"


def sync_task_to_claude_tasks(
    task_db: TaskDB,
    flow_id: str,
    conversation_id: str,
    parent_claude_task_id: Optional[str] = None
) -> Optional[str]:
    """
    Create corresponding Claude Code Task if sync is enabled.
    
    Background agents can read ~/.claude/tasks/ to see completed tasks,
    dependencies, and results without needing context injection.
    
    Args:
        task_db: Orchestration task database model
        flow_id: Flow ID for end-to-end tracking
        conversation_id: Conversation ID
        parent_claude_task_id: Parent Claude Code task ID if this is a child task
        
    Returns:
        Claude Code task ID if created, None otherwise
    """
    if not settings.sync_to_claude_tasks:
        return None
    
    try:
        tasks_dir = get_claude_tasks_directory()
        tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Claude Code task ID
        claude_task_id = f"claude-task-{task_db.task_id}"
        
        # Map TaskStatus to Claude Code task status
        status_map = {
            TaskStatus.QUEUED: "pending",
            TaskStatus.RUNNING: "in_progress",
            TaskStatus.COMPLETED: "completed",
            TaskStatus.FAILED: "failed",
        }
        claude_status = status_map.get(task_db.status, "pending")
        
        # Create Claude Code task structure
        claude_task = {
            "id": claude_task_id,
            "title": (task_db.input_message[:100] if task_db.input_message else f"Task {task_db.task_id}"),
            "description": task_db.input_message or "",
            "status": claude_status,
            "dependencies": [parent_claude_task_id] if parent_claude_task_id else [],
            "created_at": task_db.created_at.isoformat() if task_db.created_at else datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "orchestration_task_id": task_db.task_id,
                "flow_id": flow_id,
                "conversation_id": conversation_id,
                "source": task_db.source,
            }
        }
        
        # Write to Claude Code Tasks directory
        task_file = tasks_dir / f"{claude_task_id}.json"
        with open(task_file, "w") as f:
            json.dump(claude_task, f, indent=2)
        
        logger.info(
            "claude_task_created",
            claude_task_id=claude_task_id,
            orchestration_task_id=task_db.task_id,
            flow_id=flow_id,
            conversation_id=conversation_id
        )
        
        # Update task source_metadata with Claude task ID
        source_metadata = json.loads(task_db.source_metadata or "{}")
        source_metadata["claude_task_id"] = claude_task_id
        task_db.source_metadata = json.dumps(source_metadata)
        
        return claude_task_id
        
    except Exception as e:
        logger.warning(
            "failed_to_sync_claude_task",
            task_id=task_db.task_id,
            error=str(e)
        )
        # Don't fail orchestration if sync fails
        return None


def update_claude_task_status(
    claude_task_id: str,
    status: str,
    result: Optional[str] = None
) -> bool:
    """
    Update Claude Code Task status when orchestration task completes.
    
    Args:
        claude_task_id: Claude Code task ID
        status: New status ("completed", "failed", etc.)
        result: Task result (optional)
        
    Returns:
        True if update succeeded, False otherwise
    """
    if not settings.sync_to_claude_tasks:
        return False
    
    try:
        tasks_dir = get_claude_tasks_directory()
        task_file = tasks_dir / f"{claude_task_id}.json"
        
        if not task_file.exists():
            logger.warning(
                "claude_task_file_not_found",
                claude_task_id=claude_task_id
            )
            return False
        
        # Read existing task
        with open(task_file) as f:
            claude_task = json.load(f)
        
        # Update status and result
        claude_task["status"] = status
        claude_task["updated_at"] = datetime.now(timezone.utc).isoformat()
        if result:
            claude_task["result"] = result
        
        # Write back
        with open(task_file, "w") as f:
            json.dump(claude_task, f, indent=2)
        
        logger.info(
            "claude_task_status_updated",
            claude_task_id=claude_task_id,
            status=status
        )
        
        return True
        
    except Exception as e:
        logger.warning(
            "failed_to_update_claude_task_status",
            claude_task_id=claude_task_id,
            error=str(e)
        )
        # Don't fail orchestration if sync fails
        return False
