# Sentry REST API

## Purpose
FastAPI REST wrapper for Sentry client, exposing HTTP endpoints for Sentry operations.

## Architecture
- **Layer:** API/Service Layer
- **Depends on:** `integrations/packages/sentry_client/`
- **Exposes:** REST HTTP endpoints on port 8030

## Key Files
- `sentry_rest_api/routes.py` (135 lines): FastAPI endpoints
- `sentry_rest_api/__main__.py`: Entry point

## Endpoints

### POST /issues/{issue_id}/comments
Add comment to Sentry issue.
```json
{
  "comment": "Agent analysis: Root cause identified"
}
```

### PATCH /issues/{issue_id}/status
Update issue status.
```json
{
  "status": "resolved"
}
```

### GET /issues/{issue_id}
Get issue details.

## Usage
```bash
# Start server
python -m sentry_rest_api

# Add comment
curl -X POST http://localhost:8030/issues/123/comments \
  -H "Content-Type: application/json" \
  -d '{"comment": "Fixed"}'
```

## Configuration
```bash
SENTRY_AUTH_TOKEN=sntrys_xxx
SENTRY_ORGANIZATION=my-org
PORT=8030
```
