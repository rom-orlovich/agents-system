from datetime import datetime

MIGRATION_ID = "004"
MIGRATION_NAME = "create_conversation_tables"
CREATED_AT = datetime(2026, 1, 30)

UP_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_id VARCHAR(50) NOT NULL REFERENCES installations(id),
    provider VARCHAR(20) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    context JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_installation
    ON conversations(installation_id);

CREATE INDEX idx_conversations_provider
    ON conversations(provider);

CREATE INDEX idx_conversations_external_id
    ON conversations(external_id);

CREATE UNIQUE INDEX idx_conversations_unique
    ON conversations(installation_id, provider, external_id);

CREATE INDEX idx_conversations_updated
    ON conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation
    ON conversation_messages(conversation_id, created_at DESC);

CREATE INDEX idx_messages_created
    ON conversation_messages(created_at DESC);

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
DROP INDEX IF EXISTS idx_messages_created;
DROP INDEX IF EXISTS idx_messages_conversation;
DROP TABLE IF EXISTS conversation_messages;
DROP INDEX IF EXISTS idx_conversations_updated;
DROP INDEX IF EXISTS idx_conversations_unique;
DROP INDEX IF EXISTS idx_conversations_external_id;
DROP INDEX IF EXISTS idx_conversations_provider;
DROP INDEX IF EXISTS idx_conversations_installation;
DROP TABLE IF EXISTS conversations;
"""


async def up(connection):
    await connection.execute(UP_SQL)


async def down(connection):
    await connection.execute(DOWN_SQL)
