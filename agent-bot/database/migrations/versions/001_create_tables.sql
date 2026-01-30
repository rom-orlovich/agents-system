-- Migration: 001 - Create base tables
-- Created: 2026-01-30

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

CREATE INDEX idx_installations_platform ON installations(platform);
CREATE INDEX idx_installations_org_id ON installations(organization_id);
CREATE INDEX idx_installations_active ON installations(is_active) WHERE is_active = TRUE;

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

CREATE INDEX idx_tasks_installation ON tasks(installation_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX idx_tasks_pending ON tasks(priority, created_at) WHERE status = 'pending';

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

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
