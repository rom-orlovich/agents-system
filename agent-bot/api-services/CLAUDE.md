# API Services

> REST API wrappers for external services.

## Overview

API Services provide REST endpoints that wrap external APIs. MCP servers call these services for actual API operations. This separation keeps API keys isolated in service containers.

## Containers

| Service | Port | Purpose |
|---------|------|---------|
| GitHub API | 3001 | GitHub REST API wrapper |
| Jira API | 3002 | Jira REST API wrapper |
| Slack API | 3003 | Slack Web API wrapper |
| Sentry API | 3004 | Sentry API wrapper |

## Architecture

```
MCP Servers
     │
     │ HTTP Requests
     ▼
┌─────────────────────────────────────────────────────┐
│               API Services                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │  │
│  │  API    │ │  API    │ │  API    │ │  API    │  │
│  │ :3001   │ │ :3002   │ │ :3003   │ │ :3004   │  │
│  │         │ │         │ │         │ │         │  │
│  │ Token:  │ │ Token:  │ │ Token:  │ │ Token:  │  │
│  │ GITHUB_ │ │ JIRA_   │ │ SLACK_  │ │ SENTRY_ │  │
│  │ TOKEN   │ │ API_KEY │ │ BOT_    │ │ DSN     │  │
│  │         │ │         │ │ TOKEN   │ │         │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────┘
     │
     │ HTTPS
     ▼
External APIs (GitHub, Jira, Slack, Sentry)
```

## Security Model

API keys are ONLY stored in API service containers:
- GitHub token → github-api container only
- Jira credentials → jira-api container only
- Slack bot token → slack-api container only
- Sentry DSN → sentry-api container only

MCP servers and agent engines have NO access to API keys.

## GitHub API Service

**Endpoints**:
```
GET  /issues/{owner}/{repo}/{number}
POST /issues/{owner}/{repo}/{number}/comments
GET  /pulls/{owner}/{repo}/{number}
POST /pulls/{owner}/{repo}/{number}/reviews
GET  /repos/{owner}/{repo}/contents/{path}
POST /repos/{owner}/{repo}/contents/{path}
```

**Environment**:
```bash
GITHUB_TOKEN=ghp_xxx
```

## Jira API Service

**Endpoints**:
```
GET  /issues/{issue_key}
POST /issues/{issue_key}/comments
GET  /search?jql={query}
POST /issues/{issue_key}/transitions
GET  /projects
```

**Environment**:
```bash
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
JIRA_API_TOKEN=xxx
```

## Slack API Service

**Endpoints**:
```
POST /chat/postMessage
GET  /conversations/history
POST /reactions/add
GET  /users/info
GET  /conversations/list
```

**Environment**:
```bash
SLACK_BOT_TOKEN=xoxb-xxx
```

## Sentry API Service

**Endpoints**:
```
GET  /issues/{issue_id}
GET  /projects/{project}/issues
PUT  /issues/{issue_id}
GET  /events/{event_id}
```

**Environment**:
```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx
```

## Docker Compose

```yaml
# docker-compose.services.yml
services:
  github-api:
    build: ./github-api
    ports:
      - "3001:3001"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}

  jira-api:
    build: ./jira-api
    ports:
      - "3002:3002"
    environment:
      - JIRA_URL=${JIRA_URL}
      - JIRA_EMAIL=${JIRA_EMAIL}
      - JIRA_API_TOKEN=${JIRA_API_TOKEN}

  slack-api:
    build: ./slack-api
    ports:
      - "3003:3003"
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}

  sentry-api:
    build: ./sentry-api
    ports:
      - "3004:3004"
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - SENTRY_AUTH_TOKEN=${SENTRY_AUTH_TOKEN}
```

## Health Checks

```bash
curl http://localhost:3001/health  # GitHub
curl http://localhost:3002/health  # Jira
curl http://localhost:3003/health  # Slack
curl http://localhost:3004/health  # Sentry
```

## Error Handling

All services return standardized error responses:

```json
{
  "error": "not_found",
  "message": "Issue PROJ-999 not found",
  "status_code": 404
}
```

## Testing

```bash
cd api-services/github-api && pytest
cd api-services/jira-api && pytest
cd api-services/slack-api && pytest
cd api-services/sentry-api && pytest
```
