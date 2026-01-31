# OAuth Service

> Multi-tenant OAuth token management service for GitHub, Jira, and Slack integrations.

## Purpose

The OAuth Service manages OAuth tokens for multi-tenant installations. It handles OAuth flows, token storage, token refresh, and provides token lookup APIs for other services.

## Architecture

```
User (GitHub/Jira/Slack)
         │
         │ OAuth Authorization
         ▼
┌─────────────────────────────────────┐
│      OAuth Service :6000           │
│                                     │
│  1. Initiate OAuth flow            │
│  2. Handle callback                │
│  3. Exchange code for token        │
│  4. Store token in PostgreSQL      │
│  5. Provide token lookup API       │
└─────────────────────────────────────┘
         │
         ▼
    PostgreSQL (token storage)
```

## Folder Structure

```
oauth-service/
├── main.py                    # FastAPI application
├── api/
│   ├── routes.py              # OAuth routes
│   └── server.py              # FastAPI app creation
├── providers/
│   ├── base.py                # Base OAuth provider
│   ├── github.py              # GitHub OAuth provider
│   ├── jira.py                # Jira OAuth provider
│   └── slack.py               # Slack OAuth provider
├── services/
│   ├── installation_service.py # Installation management
│   └── token_service.py       # Token storage and refresh
└── config/
    └── settings.py            # Configuration
```

## Business Logic

### Core Responsibilities

1. **OAuth Flow Management**: Handle OAuth authorization flows
2. **Token Storage**: Securely store OAuth tokens per organization/workspace
3. **Token Refresh**: Automatically refresh expired tokens
4. **Token Lookup**: Provide token lookup APIs for other services
5. **Installation Management**: Track OAuth app installations

## OAuth Flows

### GitHub OAuth

1. User clicks "Install GitHub App"
2. Redirected to GitHub authorization page
3. User authorizes installation
4. GitHub redirects to `/oauth/github/callback` with code
5. Service exchanges code for access token
6. Token stored in database with organization ID

### Jira OAuth

1. User initiates Jira OAuth
2. Redirected to Jira authorization page
3. User authorizes access
4. Jira redirects to `/oauth/jira/callback` with code
5. Service exchanges code for access token + refresh token
6. Tokens stored in database

### Slack OAuth

1. User clicks "Add to Slack"
2. Redirected to Slack authorization page
3. User authorizes installation
4. Slack redirects to `/oauth/slack/callback` with code
5. Service exchanges code for access token
6. Token stored in database with workspace ID

## API Endpoints

### OAuth Flows

| Endpoint                  | Method | Purpose               |
| ------------------------- | ------ | --------------------- |
| `/oauth/github/authorize` | GET    | Initiate GitHub OAuth |
| `/oauth/github/callback`  | GET    | GitHub OAuth callback |
| `/oauth/jira/authorize`   | GET    | Initiate Jira OAuth   |
| `/oauth/jira/callback`    | GET    | Jira OAuth callback   |
| `/oauth/slack/authorize`  | GET    | Initiate Slack OAuth  |
| `/oauth/slack/callback`   | GET    | Slack OAuth callback  |

### Token Management

| Endpoint                              | Method | Purpose                    |
| ------------------------------------- | ------ | -------------------------- |
| `/tokens/{provider}/{org_id}`         | GET    | Get token for organization |
| `/tokens/{provider}/{org_id}`         | POST   | Store/update token         |
| `/tokens/{provider}/{org_id}/refresh` | POST   | Refresh token              |

### Installations

| Endpoint                  | Method | Purpose                  |
| ------------------------- | ------ | ------------------------ |
| `/installations`          | GET    | List installations       |
| `/installations/{org_id}` | GET    | Get installation details |
| `/installations/{org_id}` | DELETE | Uninstall app            |

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system

# GitHub OAuth
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_REDIRECT_URI=http://localhost:6000/oauth/github/callback

# Jira OAuth
JIRA_CLIENT_ID=xxx
JIRA_CLIENT_SECRET=xxx
JIRA_REDIRECT_URI=http://localhost:6000/oauth/jira/callback

# Slack OAuth
SLACK_CLIENT_ID=xxx
SLACK_CLIENT_SECRET=xxx
SLACK_REDIRECT_URI=http://localhost:6000/oauth/slack/callback
```

## Token Storage

Tokens stored in PostgreSQL:

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider, organization_id)
);
```

## Token Refresh

Service automatically refreshes expired tokens:

1. Check token expiration before use
2. If expired, use refresh token to get new access token
3. Update stored token in database
4. Return new token to caller

## Health Check

```bash
curl http://localhost:6000/health
```

## Related Services

- **github-api**: Uses this service to lookup OAuth tokens
- **jira-api**: Uses this service to lookup OAuth tokens
- **slack-api**: Uses this service to lookup OAuth tokens
- **dashboard-api**: Displays installation status
