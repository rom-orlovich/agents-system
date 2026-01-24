#!/usr/bin/env python3
"""Migration script to add missing columns to conversations table."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings


async def run_migration():
    """Run migration to add missing columns to conversations table."""
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        # Check if columns already exist by trying to query them
        # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
        # So we'll use a try-except approach
        
        columns_to_add = [
            ("initiated_task_id", "VARCHAR(255)"),
            ("flow_id", "VARCHAR(255)"),
            ("total_cost_usd", "REAL NOT NULL DEFAULT 0.0"),
            ("total_tasks", "INTEGER NOT NULL DEFAULT 0"),
            ("total_duration_seconds", "REAL NOT NULL DEFAULT 0.0"),
            ("started_at", "TIMESTAMP"),
            ("completed_at", "TIMESTAMP"),
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                # Try to query the column - if it exists, this will succeed
                await conn.execute(
                    text(f"SELECT {column_name} FROM conversations LIMIT 1")
                )
                print(f"✓ Column {column_name} already exists, skipping...")
            except Exception:
                # Column doesn't exist, add it
                try:
                    await conn.execute(
                        text(f"ALTER TABLE conversations ADD COLUMN {column_name} {column_def}")
                    )
                    print(f"✓ Added column {column_name}")
                except Exception as e:
                    print(f"✗ Failed to add column {column_name}: {e}")
                    raise
        
        # Create index on flow_id if it doesn't exist
        try:
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_conversations_flow_id ON conversations(flow_id)")
            )
            print("✓ Created index on flow_id")
        except Exception as e:
            print(f"✗ Failed to create index: {e}")
            # Don't raise - index creation failure is not critical
    
    await engine.dispose()
    print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    print("Running migration: Add missing columns to conversations table...")
    asyncio.run(run_migration())
