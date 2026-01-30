from datetime import datetime

MIGRATION_ID = "001"
MIGRATION_NAME = "create_installations"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TABLE IF NOT EXISTS installations (
    id VARCHAR(50) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    webhook_secret VARCHAR(255) NOT NULL,
    installed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    installed_by VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT installations_platform_org_unique 
        UNIQUE(platform, organization_id)
);

CREATE INDEX idx_installations_platform 
    ON installations(platform);

CREATE INDEX idx_installations_org_id 
    ON installations(organization_id);

CREATE INDEX idx_installations_active 
    ON installations(is_active) 
    WHERE is_active = TRUE;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_installations_updated_at
    BEFORE UPDATE ON installations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS update_installations_updated_at ON installations;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP INDEX IF EXISTS idx_installations_active;
DROP INDEX IF EXISTS idx_installations_org_id;
DROP INDEX IF EXISTS idx_installations_platform;
DROP TABLE IF EXISTS installations;
"""


async def up(connection):
    await connection.execute(UP_SQL)


async def down(connection):
    await connection.execute(DOWN_SQL)
