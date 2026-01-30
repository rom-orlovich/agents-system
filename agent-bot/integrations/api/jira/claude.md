# Jira REST API - Claude Configuration

## Component Overview

REST API providing HTTP endpoints for Jira operations.

## Purpose

- 🌐 HTTP interface for Jira operations
- 📊 Used by dashboard-api-container
- 🔄 Uses jira_client package (DRY)
- ⚡ FastAPI for endpoints

## Key Rules

- ❌ NO file > 300 lines
- ❌ NO `any` types
- ✅ Depends on `packages/jira_client`
- ✅ FastAPI for routes

## Directory Structure

```
jira/
├── jira_rest_api/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   └── routes.py        # FastAPI routes (< 300 lines)
├── Dockerfile
├── pyproject.toml
└── claude.md
```

## Endpoints

### POST /api/v1/jira/issue/{issue_key}/comment
```json
{
    "issue_key": "PROJ-123",
    "comment": "Comment text"
}
```

### GET /api/v1/jira/issue/{issue_key}
```
Response: JiraIssueResponse
```

### POST /api/v1/jira/issue
```json
{
    "project_key": "PROJ",
    "summary": "Title",
    "description": "Description",
    "issue_type": "Bug"
}
```

### POST /api/v1/jira/issue/{issue_key}/transition
```json
{
    "issue_key": "PROJ-123",
    "transition_id": "31"
}
```

### GET /health
```json
{"status": "healthy"}
```

## Implementation

### Routes
```python
from fastapi import FastAPI, HTTPException
from jira_client import JiraClient, AddCommentInput, AddCommentResponse

app = FastAPI()

@app.post("/api/v1/jira/issue/{issue_key}/comment", response_model=AddCommentResponse)
async def add_comment(issue_key: str, request: AddCommentInput):
    client = JiraClient(...)

    try:
        return await client.add_comment(request)
    except JiraClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Entry Point
```python
import uvicorn
from .routes import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
```

## Environment Variables

```bash
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=your-token
JIRA_DOMAIN=your-domain.atlassian.net
```

## Usage

### cURL
```bash
curl -X POST http://localhost:8082/api/v1/jira/issue/PROJ-123/comment \
  -H "Content-Type: application/json" \
  -d '{"issue_key":"PROJ-123","comment":"Test comment"}'
```

### Python
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://jira-rest-api:8082/api/v1/jira/issue/PROJ-123/comment",
        json={"issue_key": "PROJ-123", "comment": "Test"}
    )
```

## Testing

```python
from fastapi.testclient import TestClient
from .routes import app

client = TestClient(app)

def test_add_comment():
    response = client.post(
        "/api/v1/jira/issue/PROJ-123/comment",
        json={"issue_key": "PROJ-123", "comment": "Test"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

## Docker

### Build
```bash
docker build -f integrations/api/jira/Dockerfile -t jira-rest-api .
```

### Run
```bash
docker run -p 8082:8082 --env-file .env jira-rest-api
```

## Dependencies

- jira_client (from packages/)
- fastapi
- uvicorn

## OpenAPI Docs

Access at: `http://localhost:8082/docs`

## Summary

- 🌐 HTTP REST interface for Jira
- ⚡ FastAPI endpoints
- 🔄 Uses shared jira_client
- 📊 Used by dashboard
- ✅ < 300 lines
- ✅ NO `any` types
- 📖 Auto-generated OpenAPI docs
