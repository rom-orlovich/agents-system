# Agent Bot Dashboard

Enhanced dashboard migrated from claude-code-agent with task streaming and analytics.

## Features

- **Dashboard v1**: Static HTML/JS dashboard at `/static/`
- **Dashboard v2**: React/TypeScript dashboard at `/`
- **Task Management**: View, filter, and manage tasks
- **Real-time Updates**: WebSocket streaming of task outputs
- **Analytics**: Cost tracking, performance metrics, histograms
- **Conversations**: Chat interface for agent interactions
- **Webhook Status**: Monitor webhook configurations and events

## API Endpoints

### Dashboard
- `GET /api/status` - Machine status
- `GET /api/tasks` - List tasks with pagination
- `GET /api/tasks/{task_id}` - Task details
- `GET /api/tasks/{task_id}/logs/full` - Complete task logs
- `GET /api/agents` - List available agents

### Analytics
- `GET /api/analytics/summary` - Analytics summary
- `GET /api/analytics/costs/histogram` - Cost breakdown

### Conversations
- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{conversation_id}/messages` - Get messages

### Webhooks
- `GET /api/webhooks` - Webhook configurations
- `GET /api/webhooks/events` - Webhook events
- `GET /api/webhooks/stats` - Webhook statistics

### WebSocket
- `WS /ws` - WebSocket connection for real-time updates

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
AGENT_ENGINE_URL=http://agent-engine:8080
CORS_ORIGINS=http://localhost:3005
LOG_LEVEL=INFO
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

## Docker

```bash
# Build
docker build -t agent-bot-dashboard .

# Run
docker run -p 5000:5000 \
  -e REDIS_URL=redis://redis:6379/0 \
  -e DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system \
  agent-bot-dashboard
```

## Access

- Dashboard v1: http://localhost:5000/static/
- Dashboard v2: http://localhost:5000/
- API Docs: http://localhost:5000/docs
- Health Check: http://localhost:5000/api/health
