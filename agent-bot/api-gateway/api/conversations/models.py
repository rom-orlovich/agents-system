from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, str]
    created_at: datetime


class Conversation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    installation_id: str
    provider: Literal["github", "jira", "slack", "sentry"]
    external_id: str
    context: dict[str, str]
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = []


class ConversationContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    conversation_id: str
    messages: list[dict[str, str]]
    total_messages: int
    first_message_at: datetime
    last_message_at: datetime
