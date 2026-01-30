import json
import uuid
from datetime import datetime, timezone
from typing import Literal

import asyncpg
import structlog

from shared import Conversation, ConversationContext, Message

logger = structlog.get_logger()


class ConversationManager:
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def create_conversation(
        self,
        installation_id: str,
        provider: Literal["github", "jira", "slack", "sentry"],
        external_id: str,
        context: dict[str, str] | None = None,
    ) -> Conversation:
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ctx = context or {}

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (
                    id, installation_id, provider, external_id,
                    context, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                conversation_id,
                installation_id,
                provider,
                external_id,
                json.dumps(ctx),
                now,
                now,
            )

        logger.info(
            "conversation_created",
            conversation_id=conversation_id,
            provider=provider,
            external_id=external_id,
        )

        return Conversation(
            id=conversation_id,
            installation_id=installation_id,
            provider=provider,
            external_id=external_id,
            context=ctx,
            created_at=now,
            updated_at=now,
            messages=[],
        )

    async def get_or_create_conversation(
        self,
        installation_id: str,
        provider: Literal["github", "jira", "slack", "sentry"],
        external_id: str,
        context: dict[str, str] | None = None,
    ) -> Conversation:
        existing = await self.get_conversation(
            installation_id, provider, external_id
        )

        if existing:
            return existing

        return await self.create_conversation(
            installation_id, provider, external_id, context
        )

    async def get_conversation(
        self,
        installation_id: str,
        provider: Literal["github", "jira", "slack", "sentry"],
        external_id: str,
    ) -> Conversation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM conversations
                WHERE installation_id = $1
                  AND provider = $2
                  AND external_id = $3
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                installation_id,
                provider,
                external_id,
            )

        if row is None:
            return None

        context_data = json.loads(row["context"]) if row["context"] else {}

        return Conversation(
            id=row["id"],
            installation_id=row["installation_id"],
            provider=row["provider"],
            external_id=row["external_id"],
            context=context_data,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=[],
        )

    async def add_message(
        self,
        conversation_id: str,
        role: Literal["user", "assistant", "system"],
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> Message:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        msg_metadata = metadata or {}

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_messages (
                    id, conversation_id, role, content, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(msg_metadata),
                now,
            )

            await conn.execute(
                """
                UPDATE conversations
                SET updated_at = $1
                WHERE id = $2
                """,
                now,
                conversation_id,
            )

        logger.info(
            "message_added",
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
        )

        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=msg_metadata,
            created_at=now,
        )

    async def get_context(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> ConversationContext:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM conversation_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                conversation_id,
                limit,
            )

            count_row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    MIN(created_at) as first_at,
                    MAX(created_at) as last_at
                FROM conversation_messages
                WHERE conversation_id = $1
                """,
                conversation_id,
            )

        messages = [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in reversed(rows)
        ]

        return ConversationContext(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=count_row["total"] if count_row else 0,
            first_message_at=(
                count_row["first_at"]
                if count_row
                else datetime.now(timezone.utc)
            ),
            last_message_at=(
                count_row["last_at"] if count_row else datetime.now(timezone.utc)
            ),
        )

    async def update_conversation_context(
        self,
        conversation_id: str,
        context: dict[str, str],
    ) -> None:
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations
                SET context = $1, updated_at = $2
                WHERE id = $3
                """,
                json.dumps(context),
                now,
                conversation_id,
            )

        logger.info(
            "conversation_context_updated",
            conversation_id=conversation_id,
        )
