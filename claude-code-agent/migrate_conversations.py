#!/usr/bin/env python3
"""Database migration script to add conversation tables - standalone version."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def migrate():
    """Add conversation tables to the database."""
    from sqlalchemy import text
    from core.database import engine, init_db
    
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
                is_archived BOOLEAN NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """))
        print("✓ Created conversations table")
        
        # Create indexes for conversations
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)
        """))
        print("✓ Created conversations indexes")
        
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
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """))
        print("✓ Created conversation_messages table")
        
        # Create indexes for conversation_messages
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at)
        """))
        print("✓ Created conversation_messages indexes")
    
    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
