# OAuth Service

Centralized OAuth authentication and token management for external platform integrations.

## Purpose

OAuth Service provides:

1. **OAuth Flow Management** for GitHub, Jira/Confluence, Slack
2. **Token Storage & Refresh** with automatic renewal
3. **Installation Tracking** per organization
4. **API Token Retrieval** for other services

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OAuth Service                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                      ┌──────────────┐         │
│  │   FastAPI    │                      │   Providers  │         │
│  │   Routes     │─────────────────────▶│              │         │
│  └──────────────┘                      │ ┌──────────┐ │         │
│         │                              │ │  GitHub  │ │         │
│         │                              │ │   Jira   │ │         │
│         │                              │ │  Slack   │ │         │
│         │                              │ └──────────┘ │         │
│         │                              └──────────────┘         │
│         ▼                                     │                  │
│  ┌──────────────┐    ┌──────────────┐        │                  │
│  │ Installation │    │    Token     │◀───────┘                  │
│  │   Service    │    │   Service    │                           │
│  └──────────────┘    └──────────────┘                           │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌─────────────────────────────────────┐                        │
│  │            PostgreSQL               │                        │
│  │   oauth_installations table         │                        │
│  │   oauth_states table                │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### Providers (`providers/`)

Each provider implements `OAuthProvider` protocol:

- **GitHub** (`github.py`): GitHub App & OAuth flow
- **Jira** (`jira.py`): Atlassian OAuth 2.0 (PKCE)
- **Slack** (`slack.py`): Slack OAuth 2.0

### Services

- **InstallationService**: Manages OAuth state & installations
- **TokenService**: Retrieves and refreshes tokens

### API Routes (`api/routes.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oauth/install/{platform}` | GET | Start OAuth flow (redirect) |
| `/oauth/callback/{platform}` | GET | OAuth callback handler |
| `/oauth/installations` | GET | List all installations |
| `/oauth/installations/{id}` | DELETE | Revoke installation |
| `/oauth/token/{platform}` | GET | Get access token |

## OAuth Flows

### GitHub App Flow

```
1. User clicks "Connect GitHub"
         │
         ▼
2. GET /oauth/install/github
         │
         ▼
3. Redirect to GitHub authorization
         │
         ▼
4. User authorizes app
         │
         ▼
5. GitHub redirects to /oauth/callback/github
         │
         ▼
6. Exchange code for tokens + get installation info
         │
         ▼
7. Store in oauth_installations table
```

### Jira/Confluence (PKCE)

```
1. Generate code_verifier + code_challenge
         │
         ▼
2. Store code_verifier in oauth_states
         │
         ▼
3. Redirect with code_challenge
         │
         ▼
4. Callback with code + state
         │
         ▼
5. Exchange with code_verifier (PKCE)
```

## Configuration

Environment variables (via `config/settings.py`):

```bash
# Server
PORT=8010

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=agent
POSTGRES_PASSWORD=agent
POSTGRES_DB=agent_system

# GitHub OAuth
GITHUB_APP_ID=your_app_id
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_secret
GITHUB_PRIVATE_KEY_PATH=/path/to/key.pem

# Jira/Confluence OAuth
JIRA_CLIENT_ID=your_client_id
JIRA_CLIENT_SECRET=your_secret

# Slack OAuth
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_secret
SLACK_SIGNING_SECRET=your_signing_secret

# Callback URL base
OAUTH_CALLBACK_BASE=https://your-domain.com
```

## Database Schema

### oauth_installations

```sql
CREATE TABLE oauth_installations (
    id UUID PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,       -- github, jira, slack
    external_org_id VARCHAR(255),        -- GitHub org ID, Jira cloud ID
    external_org_name VARCHAR(255),
    external_install_id VARCHAR(255),    -- GitHub installation ID
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    scopes TEXT[],
    permissions JSONB,
    metadata JSONB,
    installed_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP
);
```

### oauth_states

```sql
CREATE TABLE oauth_states (
    state VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    code_verifier VARCHAR(255),          -- For PKCE (Jira)
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
```

## Integration with Other Services

### Indexer Worker

```python
# indexer-worker uses HybridTokenProvider
token = await token_provider.get_token("github", org_id)
# 1. Try OAuth service: GET /oauth/token/github?org_id=xxx
# 2. Fallback to static GITHUB_TOKEN env var
```

### Dashboard API

```python
# Sources API checks OAuth connection
connected = await check_oauth_connected("github")
# GET /oauth/installations?platform=github
```

### Data Sources UI

```
User creates source → UI checks OAuth status
         │
         ├─ Connected → Enable sync button
         └─ Not connected → Show "Connect OAuth" link
```

## Token Retrieval Flow

```
Service needs token → GET /oauth/token/github
         │
         ▼
TokenService.get_token()
         │
         ├─ Check token expiry
         │      │
         │      └─ Expired? → Refresh token
         │
         └─ Return decrypted token
```

## Commands

```bash
# Run locally
uv run python main.py

# Run tests
uv run pytest tests/ -v

# Test OAuth flows
uv run pytest tests/test_oauth_flows.py -v
```

## Security Notes

- Tokens stored encrypted in database
- PKCE used for public clients (Jira)
- State parameter validated against CSRF
- OAuth states expire after 10 minutes
- Tokens auto-refresh before expiry

## Provider Protocol

All providers implement:

```python
class OAuthProvider(ABC):
    def get_authorization_url(self, state: str) -> str
    async def exchange_code(self, code: str, state: str) -> OAuthTokens
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens
    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo
    async def revoke_tokens(self, tokens: OAuthTokens) -> bool
```

## Dependencies

- **PostgreSQL**: Token and installation storage
- **External APIs**: GitHub, Atlassian, Slack OAuth endpoints
