# API Services

> REST API wrappers for external services (GitHub, Jira, Slack, Sentry) with isolated credential management.

## Purpose

API Services provide REST endpoints that wrap external service APIs. They serve as a security boundary where API keys are isolated in dedicated containers. MCP servers and agent engines call these services via HTTP.

## Architecture

```
Agent Engine / MCP Server
         │
         │ HTTP Request (no credentials)
         ▼
┌─────────────────────────────────────┐
│      API Service Container         │
│                                     │
│  1. Receive HTTP request           │
│  2. Authenticate (internal token)  │
│  3. Add API credentials             │
│  4. Call external API               │
│  5. Return standardized response    │
└─────────────────────────────────────┘
         │
         │ HTTPS (with credentials)
         ▼
External API (GitHub/Jira/Slack/Sentry)
```

## Folder Structure

```
api-services/
├── README.md                 # This file
├── docker-compose.services.yml
├── github-api/
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── client/
│   │   ├── github_client.py # GitHub API client
│   │   └── multi_tenant_client.py # OAuth support
│   └── middleware/
│       └── auth.py          # Authentication
├── jira-api/                # Similar structure
├── slack-api/                # Similar structure
└── sentry-api/               # Similar structure
```

## Services

| Service    | Port | External API    | Credential Type               |
| ---------- | ---- | --------------- | ----------------------------- |
| GitHub API | 3001 | GitHub REST API | Personal Access Token / OAuth |
| Jira API   | 3002 | Jira REST API   | API Token + Email             |
| Slack API  | 3003 | Slack Web API   | Bot Token (OAuth)             |
| Sentry API | 3004 | Sentry API      | Auth Token + DSN              |

## Security Model

**Key Principle**: API keys are ONLY stored in API service containers.

- GitHub token → `github-api` container only
- Jira credentials → `jira-api` container only
- Slack bot token → `slack-api` container only
- Sentry DSN → `sentry-api` container only

MCP servers and agent engines have NO access to API keys.

## GitHub API Service

**Purpose**: Wrapper for GitHub REST API operations.

**Key Operations**:

- Issue and PR management
- Comment posting
- File content reading/writing
- Multi-tenant OAuth support

**Endpoints**:

- `GET /issues/{owner}/{repo}/{number}` - Get issue
- `POST /issues/{owner}/{repo}/{number}/comments` - Post comment
- `GET /pulls/{owner}/{repo}/{number}` - Get PR
- `POST /pulls/{owner}/{repo}/{number}/comments` - Post PR comment

**Environment**:

```bash
GITHUB_TOKEN=ghp_xxx
GITHUB_OAUTH_CLIENT_ID=xxx      # Multi-tenant
GITHUB_OAUTH_CLIENT_SECRET=xxx  # Multi-tenant
```

## Jira API Service

**Purpose**: Wrapper for Jira REST API operations.

**Key Operations**:

- Issue management
- Comment posting
- JQL search
- Transition management

**Endpoints**:

- `GET /issues/{issue_key}` - Get issue
- `POST /issues/{issue_key}/comments` - Post comment
- `GET /search?jql={query}` - Search issues

**Environment**:

```bash
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
JIRA_API_TOKEN=xxx
```

## Slack API Service

**Purpose**: Wrapper for Slack Web API operations.

**Key Operations**:

- Message posting
- Thread management
- Channel operations
- User information

**Endpoints**:

- `POST /chat/postMessage` - Post message
- `GET /conversations/history` - Get history
- `POST /reactions/add` - Add reaction

**Environment**:

```bash
SLACK_BOT_TOKEN=xoxb-xxx
```

## Sentry API Service

**Purpose**: Wrapper for Sentry API operations.

**Key Operations**:

- Issue management
- Event retrieval
- Project operations
- Alert management

**Endpoints**:

- `GET /issues/{issue_id}` - Get issue
- `GET /projects/{project}/issues` - List issues
- `PUT /issues/{issue_id}` - Update issue

**Environment**:

```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx
```

## Error Handling

Standardized error responses:

```json
{
  "error": "not_found",
  "message": "Issue PROJ-999 not found",
  "status_code": 404
}
```

## Health Checks

```bash
curl http://localhost:3001/health  # GitHub
curl http://localhost:3002/health  # Jira
curl http://localhost:3003/health  # Slack
curl http://localhost:3004/health  # Sentry
```

## Related Services

- **mcp-servers**: Call API services for external operations
- **agent-engine**: Uses API services for response posting
- **oauth-service**: Manages OAuth tokens for multi-tenant support
