# Conversation Management System

## Overview

The conversation management system provides an inbox-style interface for managing chat conversations with the Brain agent. It includes full CRUD operations, conversation history with context awareness, and persistent storage.

## Features

- **Inbox-Style Interface**: Browse and switch between multiple conversations
- **Conversation History**: All messages are persisted and can be retrieved
- **Context Awareness**: The agent receives the last 20 messages as context for each new message
- **CRUD Operations**: Create, Read, Update, and Delete conversations
- **Clear History**: Clear all messages in a conversation while keeping the conversation
- **Message Tracking**: Link messages to tasks for full traceability

## Architecture

### Database Models

#### ConversationDB
- `conversation_id`: Unique identifier
- `user_id`: User who owns the conversation
- `title`: Conversation title
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `is_archived`: Archive status
- `metadata_json`: Additional metadata

#### ConversationMessageDB
- `message_id`: Unique identifier
- `conversation_id`: Parent conversation
- `role`: Message role (user, assistant, system)
- `content`: Message content
- `task_id`: Optional link to task
- `created_at`: Creation timestamp
- `metadata_json`: Additional metadata (tokens, cost, etc.)

### API Endpoints

#### Conversation Management

**Create Conversation**
```http
POST /api/conversations
Content-Type: application/json

{
  "title": "My Conversation",
  "user_id": "default-user",
  "metadata": {}
}
```

**List Conversations**
```http
GET /api/conversations?user_id=default-user&include_archived=false&limit=50&offset=0
```

**Get Conversation**
```http
GET /api/conversations/{conversation_id}?include_messages=true
```

**Update Conversation**
```http
PUT /api/conversations/{conversation_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "is_archived": false
}
```

**Delete Conversation**
```http
DELETE /api/conversations/{conversation_id}
```

**Clear Conversation History**
```http
POST /api/conversations/{conversation_id}/clear
```

#### Message Management

**Add Message**
```http
POST /api/conversations/{conversation_id}/messages
Content-Type: application/json

{
  "role": "user",
  "content": "Hello, Brain!",
  "task_id": "task-abc123",
  "metadata": {}
}
```

**Get Messages**
```http
GET /api/conversations/{conversation_id}/messages?limit=100&offset=0
```

**Get Conversation Context**
```http
GET /api/conversations/{conversation_id}/context?max_messages=20
```

#### Chat with Context

**Send Message with Conversation Context**
```http
POST /api/chat?session_id={session_id}&conversation_id={conversation_id}
Content-Type: application/json

{
  "type": "chat.message",
  "message": "Your message here"
}
```

The agent will receive the last 20 messages from the conversation as context.

## Frontend Usage

### User Interface

The chat interface includes:

1. **Conversation Sidebar (Inbox)**
   - List of all conversations
   - New conversation button
   - Conversation actions (rename, delete)
   - Message count badge
   - Last updated timestamp

2. **Chat Panel**
   - Current conversation title
   - Message history
   - Chat input
   - Clear history button

### Creating a New Conversation

1. Click the "➕" button in the conversation sidebar
2. Enter a title for the conversation
3. Start chatting

### Switching Conversations

1. Click on any conversation in the sidebar
2. The chat panel will load the conversation history
3. All context is automatically included in new messages

### Managing Conversations

**Rename**: Click the ✏️ icon on a conversation
**Delete**: Click the 🗑️ icon on a conversation
**Clear History**: Click the 🗑️ button in the chat header

## Database Migration

Run the migration script to create the conversation tables:

```bash
python scripts/migrate_add_conversations.py
```

This creates:
- `conversations` table
- `conversation_messages` table
- Appropriate indexes and foreign keys

## Context Management

When sending a message to an existing conversation:

1. The system retrieves the last 20 messages
2. Messages are formatted as context:
   ```
   ## Previous Conversation Context:
   **User**: Previous message...
   **Assistant**: Previous response...
   
   ## Current Message:
   Your new message
   ```
3. The agent receives this full context for better continuity

## Implementation Details

### Backend Integration

The chat endpoint (`/api/chat`) now accepts an optional `conversation_id` parameter:

```python
@router.post("/chat")
async def chat_with_brain(
    message: ChatMessage,
    session_id: str,
    conversation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    # Load conversation context if conversation_id provided
    # Add user message to conversation
    # Create task with context
    # Return task_id and conversation_id
```

### Frontend Integration

The `ConversationManager` class handles:
- Loading and rendering conversations
- Managing conversation state
- Sending messages with context
- Adding assistant responses
- CRUD operations

The main `DashboardApp` integrates with `ConversationManager`:
- Initializes conversation manager on load
- Sends messages through conversation manager
- Tracks tasks for conversation updates
- Adds assistant responses when tasks complete

## Best Practices

1. **Always use conversations**: Create a conversation before chatting for full context
2. **Clear old history**: Use clear history to reset context when starting a new topic
3. **Descriptive titles**: Use clear titles to identify conversations easily
4. **Archive vs Delete**: Archive conversations you might need later, delete only when certain

## Troubleshooting

### Conversations not loading
- Check database migration was run
- Verify API endpoint is accessible
- Check browser console for errors

### Context not working
- Ensure conversation_id is passed to chat endpoint
- Verify messages are being saved to database
- Check that context retrieval query is working

### Messages not appearing
- Verify WebSocket connection is active
- Check task completion is triggering message addition
- Ensure conversation manager is initialized

## Future Enhancements

- Search within conversations
- Export conversation history
- Share conversations between users
- Conversation templates
- Auto-summarization of long conversations
- Message editing and deletion
- Conversation tags and categories
