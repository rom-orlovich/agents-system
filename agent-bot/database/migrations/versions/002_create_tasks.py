from datetime import datetime

MIGRATION_ID = "002"
MIGRATION_NAME = "create_tasks"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TYPE task_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE task_priority AS ENUM (
    'critical',
    'high',
    'normal',
    'low'
);

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(50) PRIMARY KEY,
    installation_id VARCHAR(50) NOT NULL REFERENCES installations(id),
    provider VARCHAR(20) NOT NULL,
    status task_status NOT NULL DEFAULT 'pending',
    priority task_priority NOT NULL DEFAULT 'normal',
    input_message TEXT NOT NULL,
    output TEXT,
    error TEXT,
    source_metadata JSONB NOT NULL DEFAULT '{}',
    execution_metadata JSONB NOT NULL DEFAULT '{}',
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_installation 
    ON tasks(installation_id);

CREATE INDEX idx_tasks_status 
    ON tasks(status);

CREATE INDEX idx_tasks_created 
    ON tasks(created_at DESC);

CREATE INDEX idx_tasks_pending 
    ON tasks(priority, created_at) 
    WHERE status = 'pending';

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
DROP INDEX IF EXISTS idx_tasks_pending;
DROP INDEX IF EXISTS idx_tasks_created;
DROP INDEX IF EXISTS idx_tasks_status;
DROP INDEX IF EXISTS idx_tasks_installation;
DROP TABLE IF EXISTS tasks;
DROP TYPE IF EXISTS task_priority;
DROP TYPE IF EXISTS task_status;
"""


async def up(connection):
    await connection.execute(UP_SQL)


async def down(connection):
    await connection.execute(DOWN_SQL)
