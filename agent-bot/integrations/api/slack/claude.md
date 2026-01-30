# Slack REST API

## Purpose
FastAPI REST wrapper for Slack client, exposing HTTP endpoints for Slack operations.

## Architecture
- **Layer:** API/Service Layer
- **Depends on:** `integrations/packages/slack_client/`
- **Exposes:** REST HTTP endpoints on port 8020

## Key Files
- `slack_rest_api/routes.py` (97 lines): FastAPI endpoints
- `slack_rest_api/__main__.py`: Entry point

## Endpoints

### POST /messages
Post message to Slack channel.
```json
{
  "channel": "C1234567890",
  "text": "Agent update",
  "thread_ts": "1234567890.123456"
}
```

### PATCH /messages
Update existing message.
```json
{
  "channel": "C1234567890",
  "ts": "1234567890.123456",
  "text": "Updated message"
}
```

### POST /reactions
Add reaction to message.
```json
{
  "channel": "C1234567890",
  "timestamp": "1234567890.123456",
  "name": "rocket"
}
```

## Usage
```bash
# Start server
python -m slack_rest_api

# Post message
curl -X POST http://localhost:8020/messages \
  -H "Content-Type: application/json" \
  -d '{"channel": "C123", "text": "Hello"}'
```

## Configuration
```bash
SLACK_BOT_TOKEN=xoxb-xxx
PORT=8020
```
