from datetime import datetime

MIGRATION_ID = "003"
MIGRATION_NAME = "create_analytics_tables"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TABLE IF NOT EXISTS usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(50) NOT NULL,
    installation_id VARCHAR(50) NOT NULL REFERENCES installations(id),
    provider VARCHAR(20) NOT NULL,
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,
    duration_seconds DECIMAL(10, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_created
    ON usage_metrics(created_at DESC);

CREATE INDEX idx_usage_task
    ON usage_metrics(task_id);

CREATE INDEX idx_usage_installation
    ON usage_metrics(installation_id);

CREATE INDEX idx_usage_provider
    ON usage_metrics(provider);

CREATE INDEX idx_usage_model
    ON usage_metrics(model);

ALTER TABLE installations
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_installations_last_used
    ON installations(last_used_at DESC);
"""

DOWN_SQL = """
DROP INDEX IF EXISTS idx_installations_last_used;
ALTER TABLE installations DROP COLUMN IF EXISTS last_used_at;
DROP INDEX IF EXISTS idx_usage_model;
DROP INDEX IF EXISTS idx_usage_provider;
DROP INDEX IF EXISTS idx_usage_installation;
DROP INDEX IF EXISTS idx_usage_task;
DROP INDEX IF EXISTS idx_usage_created;
DROP TABLE IF EXISTS usage_metrics;
"""


async def up(connection):
    await connection.execute(UP_SQL)


async def down(connection):
    await connection.execute(DOWN_SQL)
