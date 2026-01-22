#!/usr/bin/env python3
"""Database migration script to add conversation tables."""

import asyncio
from sqlalchemy import text
from core.database import engine, init_db


async def migrate():
    """Add conversation tables to the database."""
    print("Starting migration: Add conversation tables...")
    
    # Initialize database connection
    await init_db()
    
    async with engine.begin() as conn:
        # Create conversations table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                INDEX idx_user_id (user_id),
                INDEX idx_updated_at (updated_at)
            )
        """))
        print("✓ Created conversations table")
        
        # Create conversation_messages table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id VARCHAR(255) PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                task_id VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                INDEX idx_conversation_id (conversation_id),
                INDEX idx_created_at (created_at),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """))
        print("✓ Created conversation_messages table")
    
    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
