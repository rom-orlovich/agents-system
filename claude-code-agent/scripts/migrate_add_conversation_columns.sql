-- Database migration: Add missing columns to conversations table
-- Run this with: sqlite3 /data/db/machine.db < scripts/migrate_add_conversation_columns.sql
-- Or use: python -c "import sqlite3; conn = sqlite3.connect('/data/db/machine.db'); conn.executescript(open('scripts/migrate_add_conversation_columns.sql').read()); conn.commit()"

-- Add initiated_task_id column (nullable)
ALTER TABLE conversations ADD COLUMN initiated_task_id VARCHAR(255);

-- Add flow_id column (nullable)
ALTER TABLE conversations ADD COLUMN flow_id VARCHAR(255);

-- Add total_cost_usd column (default 0.0)
ALTER TABLE conversations ADD COLUMN total_cost_usd REAL NOT NULL DEFAULT 0.0;

-- Add total_tasks column (default 0)
ALTER TABLE conversations ADD COLUMN total_tasks INTEGER NOT NULL DEFAULT 0;

-- Add total_duration_seconds column (default 0.0)
ALTER TABLE conversations ADD COLUMN total_duration_seconds REAL NOT NULL DEFAULT 0.0;

-- Add started_at column (nullable)
ALTER TABLE conversations ADD COLUMN started_at TIMESTAMP;

-- Add completed_at column (nullable)
ALTER TABLE conversations ADD COLUMN completed_at TIMESTAMP;

-- Create index on flow_id
CREATE INDEX IF NOT EXISTS idx_conversations_flow_id ON conversations(flow_id);
