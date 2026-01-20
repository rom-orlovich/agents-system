"""Database connection and models."""
from datetime import datetime
from typing import Any, Dict, Optional
import json
import logging

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Text, Boolean, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from shared.config import settings

logger = logging.getLogger("db")

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

class TaskDB(Base):
    """Task database model."""
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    source = Column(String, index=True)
    status = Column(String, index=True)
    queued_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Metrics
    cost_usd = Column(Float, default=0.0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    
    # Context
    repository = Column(String, nullable=True)
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String, nullable=True)
    issue_key = Column(String, nullable=True)  # Jira
    
    # Metadata
    account_id = Column(String, index=True, default="unknown")
    
    # JSON Data (full task dump)
    data = Column(JSON, default={})

def init_db():
    """Initialize database tables."""
    try:
        if not inspect(engine).has_table("tasks"):
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created")
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")

    # Simple migration for account_id
    try:
        inspector = inspect(engine)
        if inspector.has_table("tasks"):
            columns = [c["name"] for c in inspector.get_columns("tasks")]
            if "account_id" not in columns:
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN account_id VARCHAR DEFAULT 'unknown'"))
                    conn.commit()
                    logger.info("Added account_id column")
    except Exception as e:
        logger.error(f"Failed to migrate DB: {e}")

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_task_to_db(task_data: Dict[str, Any]):
    """Save or update task in database."""
    db = SessionLocal()
    try:
        task_id = task_data.get("task_id")
        if not task_id:
            return

        # Check existence
        db_task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
        
        if not db_task:
            db_task = TaskDB(task_id=task_id)
            db.add(db_task)
        
        # Update fields
        db_task.source = task_data.get("source")
        db_task.status = task_data.get("status")
        
        # Timestamps
        if task_data.get("queued_at"):
            try:
                db_task.queued_at = datetime.fromisoformat(str(task_data["queued_at"]).replace("Z", "+00:00"))
            except: pass
            
        if task_data.get("completed_at"):
            try:
                db_task.completed_at = datetime.fromisoformat(str(task_data["completed_at"]).replace("Z", "+00:00"))
            except: pass
            
        # Metrics
        db_task.cost_usd = float(task_data.get("cost_usd", 0))
        db_task.input_tokens = int(task_data.get("input_tokens", 0))
        db_task.output_tokens = int(task_data.get("output_tokens", 0))
        db_task.cache_read_tokens = int(task_data.get("cache_read_tokens", 0))
        db_task.cache_creation_tokens = int(task_data.get("cache_creation_tokens", 0))
        db_task.duration_seconds = float(task_data.get("duration_seconds", 0))
        db_task.error = task_data.get("error")
        
        # Context
        db_task.repository = task_data.get("repository")
        db_task.pr_number = task_data.get("pr_number")
        db_task.pr_url = task_data.get("pr_url")
        db_task.issue_key = task_data.get("issue_key")
        
        # Identity
        if task_data.get("account_id"):
            db_task.account_id = task_data.get("account_id")
        
        # Full dump
        # Ensure data is JSON serializable (handle datetimes)
        try:
             db_task.data = json.loads(json.dumps(task_data, default=str))
        except Exception as e:
             logger.warning(f"Failed to serialize task data: {e}")
             db_task.data = {}
        
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save task to DB: {e}")
        db.rollback()
    finally:
        db.close()
