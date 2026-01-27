"""Integration tests for chat API endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import ConversationDB, ConversationMessageDB, TaskDB, SessionDB


@pytest.mark.integration
async def test_chat_creates_new_conversation_when_none_provided(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: Execute chat creates new conversation when conversation_id is not provided."""
    session_id = "test-session-001"
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id},
        json={"message": "Hello, this is a test message"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "conversation_id" in data["data"]
    assert "task_id" in data["data"]
    
    conversation_id = data["data"]["conversation_id"]

    result = await db_session.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    assert conversation is not None
    assert conversation.user_id == "default-user"
    assert conversation.title == "Hello, this is a test message"
    
    import json
    metadata = json.loads(conversation.metadata_json)
    assert metadata["source"] == "dashboard"
    assert metadata["created_from"] == "execute_chat"


@pytest.mark.integration
async def test_chat_creates_conversation_with_truncated_title(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: Conversation title is truncated to 50 characters for long messages."""
    session_id = "test-session-002"
    long_message = "A" * 100
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id},
        json={"message": long_message}
    )
    
    assert response.status_code == 200
    data = response.json()
    conversation_id = data["data"]["conversation_id"]
    
    result = await db_session.execute(
        select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    assert conversation is not None
    assert len(conversation.title) == 53
    assert conversation.title.endswith("...")


@pytest.mark.integration
async def test_chat_adds_message_to_new_conversation(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: User message is added to the newly created conversation."""
    session_id = "test-session-003"
    message_content = "Test message content"
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id},
        json={"message": message_content}
    )
    
    assert response.status_code == 200
    data = response.json()
    conversation_id = data["data"]["conversation_id"]
    task_id = data["data"]["task_id"]
    
    result = await db_session.execute(
        select(ConversationMessageDB).where(
            ConversationMessageDB.conversation_id == conversation_id
        )
    )
    messages = result.scalars().all()
    
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == message_content
    assert messages[0].task_id == task_id


@pytest.mark.integration
async def test_chat_creates_task_with_conversation_id(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: Task is created with conversation_id in source_metadata."""
    session_id = "test-session-004"
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id},
        json={"message": "Create a task"}
    )
    
    assert response.status_code == 200
    data = response.json()
    conversation_id = data["data"]["conversation_id"]
    task_id = data["data"]["task_id"]
    
    result = await db_session.execute(
        select(TaskDB).where(TaskDB.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    
    assert task is not None
    assert task.assigned_agent == "brain"
    assert task.source == "dashboard"
    
    import json
    source_metadata = json.loads(task.source_metadata)
    assert source_metadata["conversation_id"] == conversation_id
    assert source_metadata["has_context"] is False


@pytest.mark.integration
async def test_chat_uses_existing_conversation_when_provided(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: When conversation_id is provided, uses existing conversation."""
    session_id = "test-session-005"
    
    conversation = ConversationDB(
        conversation_id="existing-conv-001",
        user_id="default-user",
        title="Existing Conversation",
    )
    db_session.add(conversation)
    await db_session.commit()
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id, "conversation_id": "existing-conv-001"},
        json={"message": "New message in existing conversation"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["conversation_id"] == "existing-conv-001"
    
    result = await db_session.execute(
        select(ConversationMessageDB).where(
            ConversationMessageDB.conversation_id == "existing-conv-001"
        )
    )
    messages = result.scalars().all()
    
    assert len(messages) == 1
    assert messages[0].content == "New message in existing conversation"


@pytest.mark.integration
async def test_chat_includes_context_from_existing_conversation(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: When using existing conversation, includes previous messages as context."""
    session_id = "test-session-006"
    conversation_id = "existing-conv-002"
    
    conversation = ConversationDB(
        conversation_id=conversation_id,
        user_id="default-user",
        title="Conversation with History",
    )
    db_session.add(conversation)
    
    previous_message = ConversationMessageDB(
        message_id="msg-001",
        conversation_id=conversation_id,
        role="user",
        content="Previous message",
    )
    db_session.add(previous_message)
    await db_session.commit()
    
    response = await client.post(
        "/api/chat",
        params={"session_id": session_id, "conversation_id": conversation_id},
        json={"message": "Follow-up message"}
    )
    
    assert response.status_code == 200
    data = response.json()
    task_id = data["data"]["task_id"]
    
    result = await db_session.execute(
        select(TaskDB).where(TaskDB.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    
    assert task is not None
    assert "Previous Conversation Context" in task.input_message
    assert "Previous message" in task.input_message
    assert "Follow-up message" in task.input_message
    
    import json
    source_metadata = json.loads(task.source_metadata)
    assert source_metadata["has_context"] is True


@pytest.mark.integration
async def test_chat_creates_session_if_not_exists(client: AsyncClient, db_session: AsyncSession):
    """REQUIREMENT: Creates new session if session_id doesn't exist."""
    new_session_id = "new-session-001"
    
    result = await db_session.execute(
        select(SessionDB).where(SessionDB.session_id == new_session_id)
    )
    existing_session = result.scalar_one_or_none()
    assert existing_session is None
    
    response = await client.post(
        "/api/chat",
        params={"session_id": new_session_id},
        json={"message": "Test message"}
    )
    
    assert response.status_code == 200
    
    result = await db_session.execute(
        select(SessionDB).where(SessionDB.session_id == new_session_id)
    )
    session = result.scalar_one_or_none()
    
    assert session is not None
    assert session.user_id == "default-user"
    assert session.machine_id == "claude-agent-001"
