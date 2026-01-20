
import sys
import os
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database import SessionLocal, TaskDB
from shared.models import TaskStatus, TaskSource

def seed_data():
    print("🌱 Seeding dashboard with dummy data...")
    db = SessionLocal()
    
    # Clear existing entries if you want, but for now we just append
    # db.query(TaskDB).delete()
    
    tasks = [
        {
            "task_id": "task-demo-1",
            "source": TaskSource.JIRA,
            "status": TaskStatus.COMPLETED,
            "cost_usd": 0.05,
            "input_tokens": 1500,
            "output_tokens": 500,
            "duration_seconds": 45.2,
            "queued_at": datetime.utcnow() - timedelta(minutes=30),
            "updated_at": datetime.utcnow() - timedelta(minutes=29),
            "account_id": "alice_dev",
            "data": {"email": "alice@example.com", "issue_key": "KAN-123"}
        },
        {
            "task_id": "task-demo-2",
            "source": TaskSource.GITHUB,
            "status": TaskStatus.FAILED,
            "cost_usd": 0.01,
            "input_tokens": 800,
            "output_tokens": 100,
            "duration_seconds": 12.5,
            "queued_at": datetime.utcnow() - timedelta(hours=2),
            "updated_at": datetime.utcnow() - timedelta(hours=1, minutes=59),
            "account_id": "bob_manager",
            "data": {"email": "bob@example.com", "repository": "agents-prod/demo"}
        },
        {
            "task_id": "task-demo-3",
            "source": TaskSource.SLACK,
            "status": TaskStatus.EXECUTING,
            "cost_usd": 0.02,
            "input_tokens": 1200,
            "output_tokens": 0,
            "duration_seconds": 120.0,
            "queued_at": datetime.utcnow() - timedelta(minutes=5),
            "updated_at": datetime.utcnow(),
            "account_id": "alice_dev",
            "data": {"email": "alice@example.com", "channel": "#general"}
        }
    ]

    for t in tasks:
        # Check if exists
        existing = db.query(TaskDB).filter(TaskDB.task_id == t["task_id"]).first()
        if existing:
            continue
            
        task = TaskDB(
            task_id=t["task_id"],
            source=t["source"],
            status=t["status"],
            cost_usd=t["cost_usd"],
            input_tokens=t["input_tokens"],
            output_tokens=t["output_tokens"],
            duration_seconds=t["duration_seconds"],
            queued_at=t["queued_at"],
            updated_at=t["updated_at"],
            account_id=t["account_id"],
            data=t["data"]
        )
        # Migrate specific fields from data
        if "issue_key" in t["data"]:
            task.issue_key = t["data"]["issue_key"]
        if "repository" in t["data"]:
            task.repository = t["data"]["repository"]
            
        db.add(task)
        
    db.commit()
    print(f"✅ added {len(tasks)} dummy tasks.")
    print("Refresh the dashboard to see them!")
    db.close()

if __name__ == "__main__":
    seed_data()
