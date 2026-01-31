# OAuth Service

> Multi-tenant OAuth token management service for GitHub, Jira, and Slack integrations.

## Purpose

The OAuth Service manages OAuth tokens for **multi-tenant, organization-level installations**. Organizations install the OAuth app once, and all services use organization-level tokens - **no individual user accounts required**.

**Key Benefits:**

- **Organization-level installations**: One installation per GitHub org/Slack workspace/Jira site
- **No user accounts needed**: Tokens stored per organization, not per user
- **Automatic token refresh**: Handles token expiration and refresh automatically
- **Centralized token management**: Single source of truth for all OAuth tokens

## Architecture

```
User (GitHub/Jira/Slack)
         │
         │ OAuth Authorization
         ▼
┌─────────────────────────────────────┐
│      OAuth Service :8010           │
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

| Endpoint                     | Method | Purpose                |
| ---------------------------- | ------ | ---------------------- |
| `/oauth/install/{platform}`  | GET    | Start OAuth flow       |
| `/oauth/callback/{platform}` | GET    | OAuth callback handler |

**Platforms**: `github`, `slack`, `jira`

### Installation Management

| Endpoint                                   | Method | Purpose             |
| ------------------------------------------ | ------ | ------------------- |
| `/oauth/installations?platform={platform}` | GET    | List installations  |
| `/oauth/installations/{installation_id}`   | DELETE | Revoke installation |

### Token Lookup

| Endpoint                                  | Method | Purpose                       |
| ----------------------------------------- | ------ | ----------------------------- |
| `/oauth/token/{platform}?org_id={org_id}` | GET    | Get token for organization    |
| `/oauth/token/{platform}?install_id={id}` | GET    | Get GitHub installation token |

## Environment Variables

See `.env.example` for complete configuration. Key variables:

```bash
PORT=8010
BASE_URL=http://localhost:8010

DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system

# GitHub OAuth (OAuth App or GitHub App)
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_APP_ID=123456  # For GitHub Apps
GITHUB_APP_NAME=my-app
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=xxx

# Jira OAuth
JIRA_CLIENT_ID=xxx
JIRA_CLIENT_SECRET=xxx

# Slack OAuth
SLACK_CLIENT_ID=xxx
SLACK_CLIENT_SECRET=xxx
SLACK_SIGNING_SECRET=xxx
SLACK_STATE_SECRET=xxx

# Token Encryption
TOKEN_ENCRYPTION_KEY=xxx  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Note**: OAuth callback URLs should match your `BASE_URL`:

- `{BASE_URL}/oauth/callback/github`
- `{BASE_URL}/oauth/callback/slack`
- `{BASE_URL}/oauth/callback/jira`

## Token Storage

Tokens are stored in the shared `installations` table (managed by `agent-engine` models). The service uses the `Installation` model which includes:

- `platform` - Provider (github, slack, jira)
- `external_org_id` - **Organization/workspace identifier** (not user ID)
- `external_org_name` - Organization name
- `access_token` - OAuth access token (scoped to organization)
- `refresh_token` - OAuth refresh token (if supported)
- `token_expires_at` - Token expiration timestamp
- `scopes` - Granted OAuth scopes
- `status` - Installation status (ACTIVE, REVOKED)
- `metadata_json` - Additional provider-specific data

**How it works:**

1. Organization admin installs OAuth app (GitHub org/Slack workspace/Jira site)
2. Installation stored with `external_org_id` (e.g., `github.com/acme-corp`, `T01234567` for Slack)
3. All services lookup tokens by `org_id` - no user accounts needed
4. If organization reinstalls, existing installation is updated (not duplicated)

## Webhook Secrets vs OAuth Installations

**Important distinction:**

- **OAuth Installations**: Per-organization (each org installs → gets their own tokens)
- **Webhook Secrets**: App-level (one secret for all webhooks from that app)

**Webhook secrets come from OAuth app configuration:**

- **GitHub**: Webhook secret set when creating GitHub App (same secret for all installations)
- **Slack**: Signing secret from Slack app Basic Information (same secret for all workspaces)
- **Jira**: Webhook secret configured in Jira app settings

**You still need to configure webhook secrets in environment variables**, but they come from the OAuth app settings (not from individual installations):

```bash
# These are app-level secrets (one per app, not per installation)
GITHUB_WEBHOOK_SECRET=xxx  # From GitHub App settings
SLACK_SIGNING_SECRET=xxx    # From Slack app Basic Information
JIRA_WEBHOOK_SECRET=xxx     # From Jira app settings
```

**Result**: Once you configure the OAuth app and set webhook secrets, you don't need to configure webhooks separately for each organization installation - the same webhook secret validates webhooks from all installations.

## Token Refresh

Service automatically refreshes expired tokens:

1. Check token expiration before use
2. If expired, use refresh token to get new access token
3. Update stored token in database
4. Return new token to caller

## Setup

For detailed setup instructions, see **[SETUP.md](./SETUP.md)**.

Quick start:

```bash
# Copy environment file
cp .env.example .env

# Configure OAuth credentials in .env
# See SETUP.md for OAuth app configuration

# Start service
cd agent-bot
docker-compose up -d oauth-service postgres

# Verify
curl http://localhost:8010/health
```

## Health Check

```bash
curl http://localhost:8010/health
```

## Related Services

- **github-api**: Uses this service to lookup OAuth tokens
- **jira-api**: Uses this service to lookup OAuth tokens
- **slack-api**: Uses this service to lookup OAuth tokens
- **dashboard-api**: Displays installation status
