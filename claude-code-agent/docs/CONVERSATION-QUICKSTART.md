# Conversation Management - Quick Start Guide

## Setup (One-Time)

### 1. Run Database Migration

```bash
cd /Users/romo/projects/agents-prod/claude-code-agent
python scripts/migrate_add_conversations.py
```

This creates the necessary database tables for conversation management.

### 2. Restart the Application

```bash
make restart
# or
docker-compose restart
```

## Using Conversations

### Creating Your First Conversation

1. Open the dashboard: `http://localhost:8000`
2. Navigate to the **💬 Chat** tab
3. Click the **➕** button in the conversation sidebar
4. Enter a title (e.g., "Project Planning")
5. Click OK

### Chatting with Context

1. Select a conversation from the sidebar
2. Type your message in the input box
3. Press Enter or click Send
4. The agent receives the last 20 messages as context automatically

### Managing Conversations

#### Rename a Conversation
- Hover over a conversation
- Click the ✏️ (edit) icon
- Enter new title

#### Delete a Conversation
- Hover over a conversation
- Click the 🗑️ (delete) icon
- Confirm deletion

#### Clear Conversation History
- Open a conversation
- Click the 🗑️ button in the chat header
- Confirm clearing

## API Examples

### Create a Conversation via API

```bash
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Test Conversation",
    "user_id": "default-user"
  }'
```

### List All Conversations

```bash
curl http://localhost:8000/api/conversations?user_id=default-user
```

### Send a Message with Context

```bash
# First, get a conversation_id from the list above
CONV_ID="conv-abc123"
SESSION_ID="session-xyz789"

curl -X POST "http://localhost:8000/api/chat?session_id=$SESSION_ID&conversation_id=$CONV_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chat.message",
    "message": "What did we discuss earlier?"
  }'
```

### Get Conversation History

```bash
curl http://localhost:8000/api/conversations/$CONV_ID/messages
```

## Features at a Glance

✅ **Persistent History**: All conversations are saved to database  
✅ **Context Awareness**: Agent knows previous messages  
✅ **Inbox Interface**: Easy conversation switching  
✅ **Full CRUD**: Create, read, update, delete operations  
✅ **Message Tracking**: Link messages to tasks  
✅ **Clear History**: Reset context without deleting conversation  

## Tips

1. **Use descriptive titles**: Makes finding conversations easier
2. **Create separate conversations**: For different topics/projects
3. **Clear history when needed**: Start fresh on new topics
4. **Check message count**: Badge shows number of messages

## Keyboard Shortcuts

- **Enter**: Send message
- **Click conversation**: Switch to that conversation

## What's Next?

- The agent maintains context across messages
- All messages are linked to tasks for traceability
- You can have unlimited conversations
- Each conversation maintains its own context

## Troubleshooting

**Problem**: Conversations not showing  
**Solution**: Run the migration script and restart the app

**Problem**: Messages not saving  
**Solution**: Check database connection and logs

**Problem**: No context in responses  
**Solution**: Ensure you're using a conversation (not just chat)

## Need Help?

Check the full documentation: `docs/CONVERSATION-MANAGEMENT.md`
