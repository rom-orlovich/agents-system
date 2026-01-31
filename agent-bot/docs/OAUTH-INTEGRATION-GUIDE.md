# OAuth Integration Guide - Multi-Tenant App Installation

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Database Models](#2-database-models)
3. [OAuth Service Implementation](#3-oauth-service-implementation)
4. [GitHub App Integration](#4-github-app-integration)
5. [Slack App Integration](#5-slack-app-integration)
6. [Jira OAuth Integration](#6-jira-oauth-integration)
7. [Multi-Tenant Routing](#7-multi-tenant-routing)
8. [Migration Plan](#8-migration-plan)
9. [Security Considerations](#9-security-considerations)

---

## 1. Architecture Overview

### Current State (Static Tokens)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ github-api  │    │  jira-api   │    │  slack-api  │
│ (port 3001) │    │ (port 3002) │    │ (port 3003) │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ GITHUB_TOKEN│    │JIRA_API_TOKEN    │SLACK_BOT_TOKEN
│ (env var)   │    │ (env var)   │    │ (env var)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                         ↓
              Single organization only
```

**Problem**: Current architecture supports only ONE organization per platform.

### Target State (OAuth Multi-Tenant)

```
┌─────────────────────────────────────────────────────────┐
│                    oauth-service                         │
│                    (new service)                         │
├─────────────────────────────────────────────────────────┤
│  GET  /install/{platform}          → Start OAuth flow   │
│  GET  /callback/{platform}         → Handle callback    │
│  GET  /installations/{platform}    → List installations │
│  DELETE /installations/{id}        → Revoke access      │
└─────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   PostgreSQL                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │              installations table                 │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ id | platform | org_id | tokens | scopes | ...  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ github-api  │    │  jira-api   │    │  slack-api  │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ Get token   │    │ Get token   │    │ Get token   │
│ per request │    │ per request │    │ per request │
│ from DB     │    │ from DB     │    │ from DB     │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Solution**: Each API request includes `installation_id`, and the service fetches the appropriate token from the database.

---

## 2. Database Models

### New SQLAlchemy Models

Create file: `agent-bot/agent-engine-package/agent_engine/models/installation.py`

```python
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import String, Text, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Platform(str, Enum):
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    SENTRY = "sentry"


class InstallationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class Installation(Base):
    """Stores OAuth installations for each platform/organization."""

    __tablename__ = "installations"
    __table_args__ = (
        Index("ix_installations_platform_org", "platform", "external_org_id"),
        Index("ix_installations_platform_status", "platform", "status"),
    )

    platform: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default=InstallationStatus.ACTIVE.value
    )

    # Platform-specific identifiers
    external_org_id: Mapped[str] = mapped_column(String(255))
    external_org_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_install_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OAuth tokens (encrypted in production)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # GitHub App specific
    private_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scopes and permissions
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Metadata
    installed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthState(Base):
    """Temporary storage for OAuth state during authorization flow."""

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(64), unique=True)
    platform: Mapped[str] = mapped_column(String(20))
    code_verifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
```

### Alembic Migration

Create file: `agent-bot/agent-engine-package/migrations/versions/001_add_installations.py`

```python
"""Add installations tables for OAuth support

Revision ID: 001_add_installations
Revises:
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = '001_add_installations'
down_revision = None  # or previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'installations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('external_org_id', sa.String(255), nullable=False),
        sa.Column('external_org_name', sa.String(255), nullable=True),
        sa.Column('external_install_id', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text, nullable=True),
        sa.Column('refresh_token', sa.Text, nullable=True),
        sa.Column('token_expires_at', sa.DateTime, nullable=True),
        sa.Column('private_key', sa.Text, nullable=True),
        sa.Column('scopes', JSON, nullable=False, default=[]),
        sa.Column('permissions', JSON, nullable=False, default={}),
        sa.Column('installed_by', sa.String(255), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('metadata', JSON, nullable=False, default={}),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    op.create_index(
        'ix_installations_platform_org',
        'installations',
        ['platform', 'external_org_id']
    )
    op.create_index(
        'ix_installations_platform_status',
        'installations',
        ['platform', 'status']
    )

    op.create_table(
        'oauth_states',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('state', sa.String(64), unique=True, nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('code_verifier', sa.String(128), nullable=True),
        sa.Column('redirect_uri', sa.String(512), nullable=True),
        sa.Column('metadata', JSON, nullable=False, default={}),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('oauth_states')
    op.drop_table('installations')
```

---

## 3. OAuth Service Implementation

### New Service Structure

```
agent-bot/
└── oauth-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── pyproject.toml
    ├── main.py
    ├── config/
    │   └── settings.py
    ├── api/
    │   ├── routes.py
    │   └── server.py
    ├── providers/
    │   ├── base.py
    │   ├── github.py
    │   ├── slack.py
    │   └── jira.py
    ├── services/
    │   ├── installation_service.py
    │   └── token_service.py
    └── tests/
        └── test_oauth_flows.py
```

### Base Provider Interface

Create file: `agent-bot/oauth-service/providers/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] | None = None


@dataclass
class InstallationInfo:
    external_org_id: str
    external_org_name: str | None
    external_install_id: str | None
    installed_by: str | None
    permissions: dict[str, str]
    metadata: dict[str, any]


class OAuthProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate the OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        pass

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token."""
        pass

    @abstractmethod
    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        """Get information about the installation/organization."""
        pass

    @abstractmethod
    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        """Revoke OAuth tokens."""
        pass
```

### Settings Configuration

Create file: `agent-bot/oauth-service/config/settings.py`

```python
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    # Service config
    port: int = 8010
    base_url: str = "https://yourdomain.com"

    # Database
    database_url: str

    # GitHub App credentials
    github_app_id: str
    github_app_name: str
    github_client_id: str
    github_client_secret: str
    github_private_key: str  # PEM file contents
    github_webhook_secret: str

    # Slack App credentials
    slack_client_id: str
    slack_client_secret: str
    slack_signing_secret: str
    slack_state_secret: str

    # Jira OAuth credentials
    jira_client_id: str
    jira_client_secret: str

    # Encryption key for tokens at rest
    token_encryption_key: str


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

### API Routes

Create file: `agent-bot/oauth-service/api/routes.py`

```python
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
import structlog

from config.settings import get_settings
from providers.github import GitHubOAuthProvider
from providers.slack import SlackOAuthProvider
from providers.jira import JiraOAuthProvider
from services.installation_service import InstallationService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])

PROVIDERS = {
    "github": GitHubOAuthProvider,
    "slack": SlackOAuthProvider,
    "jira": JiraOAuthProvider,
}


@router.get("/install/{platform}")
async def start_installation(platform: str, request: Request):
    """Start OAuth installation flow for a platform."""
    if platform not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    settings = get_settings()
    provider = PROVIDERS[platform](settings)
    installation_service = InstallationService()

    state = await installation_service.create_oauth_state(platform)
    auth_url = provider.get_authorization_url(state)

    logger.info("oauth_flow_started", platform=platform, state=state)
    return RedirectResponse(url=auth_url)


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(...),
    installation_id: str | None = Query(None),  # GitHub specific
):
    """Handle OAuth callback and store installation."""
    if platform not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    settings = get_settings()
    provider = PROVIDERS[platform](settings)
    installation_service = InstallationService()

    oauth_state = await installation_service.validate_oauth_state(state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    tokens = await provider.exchange_code(code, state)
    info = await provider.get_installation_info(tokens)

    if platform == "github" and installation_id:
        info.external_install_id = installation_id

    installation = await installation_service.create_installation(
        platform=platform,
        tokens=tokens,
        info=info,
    )

    logger.info(
        "oauth_installation_created",
        platform=platform,
        org_id=info.external_org_id,
        installation_id=str(installation.id),
    )

    return {"success": True, "installation_id": str(installation.id)}


@router.get("/installations")
async def list_installations(platform: str | None = Query(None)):
    """List all active installations."""
    installation_service = InstallationService()
    installations = await installation_service.list_installations(platform)
    return {"installations": installations}


@router.delete("/installations/{installation_id}")
async def revoke_installation(installation_id: str):
    """Revoke an installation and its tokens."""
    installation_service = InstallationService()
    success = await installation_service.revoke_installation(installation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Installation not found")
    return {"success": True}
```

---

## 4. GitHub App Integration

### Creating the GitHub App

1. Go to `https://github.com/settings/apps/new`

2. Fill in the required fields:
   ```
   App name: my-agent-bot
   Homepage URL: https://yourdomain.com
   Callback URL: https://yourdomain.com/oauth/callback/github
   Setup URL (optional): https://yourdomain.com/oauth/install/github
   Webhook URL: https://yourdomain.com/webhooks/github
   Webhook secret: [generate secure random string]
   ```

3. Set Permissions:
   ```yaml
   Repository permissions:
     - Contents: Read & write
     - Issues: Read & write
     - Pull requests: Read & write
     - Metadata: Read-only

   Organization permissions:
     - Members: Read-only

   Subscribe to events:
     - Issues
     - Pull requests
     - Push
     - Issue comments
     - Pull request reviews
   ```

4. Save these values:
   - **App ID** → `GITHUB_APP_ID`
   - **Client ID** → `GITHUB_CLIENT_ID`
   - **Client Secret** → `GITHUB_CLIENT_SECRET`
   - Download **Private Key** → `GITHUB_PRIVATE_KEY` (file contents)

### GitHub OAuth Provider Implementation

Create file: `agent-bot/oauth-service/providers/github.py`

```python
from datetime import datetime, timedelta
import jwt
import httpx
import structlog

from .base import OAuthProvider, OAuthTokens, InstallationInfo

logger = structlog.get_logger(__name__)


class GitHubOAuthProvider(OAuthProvider):
    def __init__(self, settings):
        self.settings = settings
        self.app_id = settings.github_app_id
        self.app_name = settings.github_app_name
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.private_key = settings.github_private_key
        self.redirect_uri = f"{settings.base_url}/oauth/callback/github"

    def get_authorization_url(self, state: str) -> str:
        """GitHub App installation URL."""
        return (
            f"https://github.com/apps/{self.app_name}/installations/new"
            f"?state={state}"
        )

    def _generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        now = int(datetime.utcnow().timestamp())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        """For GitHub Apps, we use installation tokens instead of OAuth."""
        return OAuthTokens(access_token="", scopes=[])

    async def get_installation_token(self, installation_id: str) -> OAuthTokens:
        """Get an installation access token for API calls."""
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            data = response.json()

        return OAuthTokens(
            access_token=data["token"],
            expires_at=datetime.fromisoformat(
                data["expires_at"].replace("Z", "+00:00")
            ),
            scopes=list(data.get("permissions", {}).keys()),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """GitHub App tokens auto-expire and need to be regenerated."""
        raise NotImplementedError("Use get_installation_token instead")

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        """Get info about a GitHub App installation."""
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/app/installations",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            installations = response.json()

        if not installations:
            raise ValueError("No installations found")

        install = installations[0]
        return InstallationInfo(
            external_org_id=str(install["account"]["id"]),
            external_org_name=install["account"]["login"],
            external_install_id=str(install["id"]),
            installed_by=None,
            permissions=install.get("permissions", {}),
            metadata={
                "account_type": install["account"]["type"],
                "repository_selection": install["repository_selection"],
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        """GitHub App tokens auto-expire, no revocation needed."""
        return True
```

### Updated GitHub API Client (Multi-Tenant)

Modify file: `agent-bot/api-services/github-api/client/github_client.py`

```python
from typing import Any
import httpx
import structlog

from services.token_service import TokenService

logger = structlog.get_logger(__name__)


class GitHubClient:
    def __init__(
        self,
        installation_id: str | None = None,
        fallback_token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout: int = 30,
    ):
        self._installation_id = installation_id
        self._fallback_token = fallback_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._token_service = TokenService()

    async def _get_token(self) -> str:
        """Get token for the current installation."""
        if self._installation_id:
            token = await self._token_service.get_github_installation_token(
                self._installation_id
            )
            if token:
                return token

        if self._fallback_token:
            return self._fallback_token

        raise ValueError("No token available for GitHub API")

    async def _get_client(self) -> httpx.AsyncClient:
        token = await self._get_token()
        if self._client is None or self._client.headers.get("Authorization") != f"Bearer {token}":
            if self._client:
                await self._client.aclose()
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=self._timeout,
            )
        return self._client

    # ... rest of methods unchanged, they use _get_client()
```

### GitHub Webhook Handler Update

Modify file: `agent-bot/api-gateway/webhooks/github/handler.py`

```python
async def handle_github_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle GitHub webhook with installation context."""
    installation_id = payload.get("installation", {}).get("id")

    if not installation_id:
        logger.warning("github_webhook_no_installation", payload_keys=list(payload.keys()))

    task_payload = {
        **payload,
        "_installation_id": str(installation_id) if installation_id else None,
    }

    # Queue task with installation context
    await queue_task(task_payload)
```

---

## 5. Slack App Integration

### Creating the Slack App

1. Go to `https://api.slack.com/apps` → Create New App → From scratch

2. Configure OAuth & Permissions:
   ```
   Redirect URLs:
     - https://yourdomain.com/oauth/callback/slack

   Bot Token Scopes:
     - chat:write
     - channels:read
     - app_mentions:read
     - users:read
     - reactions:write
   ```

3. Event Subscriptions:
   ```
   Request URL: https://yourdomain.com/webhooks/slack

   Subscribe to bot events:
     - app_mention
     - message.channels
     - reaction_added
   ```

4. Save these values:
   - **Client ID** → `SLACK_CLIENT_ID`
   - **Client Secret** → `SLACK_CLIENT_SECRET`
   - **Signing Secret** → `SLACK_SIGNING_SECRET`

### Slack OAuth Provider Implementation

Create file: `agent-bot/oauth-service/providers/slack.py`

```python
from datetime import datetime
import secrets
import httpx
import structlog

from .base import OAuthProvider, OAuthTokens, InstallationInfo

logger = structlog.get_logger(__name__)


class SlackOAuthProvider(OAuthProvider):
    def __init__(self, settings):
        self.settings = settings
        self.client_id = settings.slack_client_id
        self.client_secret = settings.slack_client_secret
        self.redirect_uri = f"{settings.base_url}/oauth/callback/slack"
        self.scopes = [
            "chat:write",
            "channels:read",
            "app_mentions:read",
            "users:read",
            "reactions:write",
        ]

    def get_authorization_url(self, state: str) -> str:
        """Generate Slack OAuth authorization URL."""
        scope_str = ",".join(self.scopes)
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={self.client_id}"
            f"&scope={scope_str}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
        )

    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        """Exchange authorization code for bot token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack OAuth error: {data.get('error')}")

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            scopes=data.get("scope", "").split(","),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh Slack bot token (if using token rotation)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack refresh error: {data.get('error')}")

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
        )

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        """Get workspace info from Slack."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/team.info",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack team.info error: {data.get('error')}")

        team = data["team"]
        return InstallationInfo(
            external_org_id=team["id"],
            external_org_name=team["name"],
            external_install_id=None,
            installed_by=None,
            permissions={scope: "granted" for scope in tokens.scopes or []},
            metadata={
                "domain": team.get("domain"),
                "icon": team.get("icon", {}).get("image_132"),
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        """Revoke Slack OAuth tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/auth.revoke",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            data = response.json()
        return data.get("ok", False)
```

---

## 6. Jira OAuth Integration

### Creating the Jira OAuth App

1. Go to `https://developer.atlassian.com/console/myapps/`
2. Create → OAuth 2.0 integration

3. Configure:
   ```
   Name: My Agent Bot
   Callback URL: https://yourdomain.com/oauth/callback/jira
   ```

4. Permissions (APIs):
   ```
   Jira API:
     - read:jira-work
     - write:jira-work
     - read:jira-user
     - offline_access (for refresh tokens)
   ```

5. Save these values:
   - **Client ID** → `JIRA_CLIENT_ID`
   - **Client Secret** → `JIRA_CLIENT_SECRET`

### Jira OAuth Provider Implementation

Create file: `agent-bot/oauth-service/providers/jira.py`

```python
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
import httpx
import structlog

from .base import OAuthProvider, OAuthTokens, InstallationInfo

logger = structlog.get_logger(__name__)


class JiraOAuthProvider(OAuthProvider):
    def __init__(self, settings):
        self.settings = settings
        self.client_id = settings.jira_client_id
        self.client_secret = settings.jira_client_secret
        self.redirect_uri = f"{settings.base_url}/oauth/callback/jira"
        self.scopes = [
            "read:jira-work",
            "write:jira-work",
            "read:jira-user",
            "offline_access",
        ]

    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return secrets.token_urlsafe(32)

    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def get_authorization_url(self, state: str, code_verifier: str | None = None) -> str:
        """Generate Jira OAuth authorization URL with PKCE."""
        if code_verifier is None:
            code_verifier = self._generate_code_verifier()

        code_challenge = self._generate_code_challenge(code_verifier)
        scope_str = " ".join(self.scopes)

        return (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={self.client_id}"
            f"&scope={scope_str}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            f"&response_type=code"
            f"&prompt=consent"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

    async def exchange_code(
        self, code: str, state: str, code_verifier: str | None = None
    ) -> OAuthTokens:
        """Exchange authorization code for tokens using PKCE."""
        async with httpx.AsyncClient() as client:
            payload = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
            if code_verifier:
                payload["code_verifier"] = code_verifier

            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.utcnow() + timedelta(seconds=data["expires_in"]),
            scopes=data.get("scope", "").split(" "),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired Jira access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=datetime.utcnow() + timedelta(seconds=data["expires_in"]),
        )

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        """Get Jira cloud site info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            resources = response.json()

        if not resources:
            raise ValueError("No accessible Jira sites found")

        site = resources[0]
        return InstallationInfo(
            external_org_id=site["id"],
            external_org_name=site["name"],
            external_install_id=None,
            installed_by=None,
            permissions={scope: "granted" for scope in tokens.scopes or []},
            metadata={
                "url": site["url"],
                "scopes": site.get("scopes", []),
                "avatar_url": site.get("avatarUrl"),
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        """Atlassian doesn't support token revocation via API."""
        return True
```

---

## 7. Multi-Tenant Routing

### Token Service for API Services

Create file: `agent-bot/oauth-service/services/token_service.py`

```python
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agent_engine.models.installation import Installation, Platform

logger = structlog.get_logger(__name__)


class TokenService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_token(
        self, platform: str, org_id: str | None = None, installation_id: str | None = None
    ) -> str | None:
        """Get active token for a platform/org combination."""
        query = select(Installation).where(
            Installation.platform == platform,
            Installation.status == "active",
        )

        if installation_id:
            query = query.where(Installation.id == installation_id)
        elif org_id:
            query = query.where(Installation.external_org_id == org_id)

        result = await self.session.execute(query)
        installation = result.scalar_one_or_none()

        if not installation:
            return None

        if installation.token_expires_at and installation.token_expires_at < datetime.utcnow():
            new_token = await self._refresh_token(installation)
            if new_token:
                return new_token
            return None

        await self._update_last_used(installation)
        return installation.access_token

    async def get_github_installation_token(self, installation_id: str) -> str | None:
        """Get GitHub App installation token (regenerates if needed)."""
        from providers.github import GitHubOAuthProvider
        from config.settings import get_settings

        query = select(Installation).where(
            Installation.platform == Platform.GITHUB.value,
            Installation.external_install_id == installation_id,
            Installation.status == "active",
        )
        result = await self.session.execute(query)
        installation = result.scalar_one_or_none()

        if not installation:
            return None

        if (
            installation.token_expires_at
            and installation.token_expires_at > datetime.utcnow() + timedelta(minutes=5)
        ):
            return installation.access_token

        provider = GitHubOAuthProvider(get_settings())
        tokens = await provider.get_installation_token(installation_id)

        installation.access_token = tokens.access_token
        installation.token_expires_at = tokens.expires_at
        await self.session.commit()

        return tokens.access_token

    async def get_all_installations(self, platform: str) -> list[Installation]:
        """Get all active installations for a platform."""
        query = select(Installation).where(
            Installation.platform == platform,
            Installation.status == "active",
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _refresh_token(self, installation: Installation) -> str | None:
        """Refresh expired token."""
        if not installation.refresh_token:
            return None

        from providers.slack import SlackOAuthProvider
        from providers.jira import JiraOAuthProvider
        from config.settings import get_settings

        settings = get_settings()
        providers = {
            Platform.SLACK.value: SlackOAuthProvider,
            Platform.JIRA.value: JiraOAuthProvider,
        }

        provider_class = providers.get(installation.platform)
        if not provider_class:
            return None

        provider = provider_class(settings)
        tokens = await provider.refresh_tokens(installation.refresh_token)

        installation.access_token = tokens.access_token
        installation.refresh_token = tokens.refresh_token or installation.refresh_token
        installation.token_expires_at = tokens.expires_at
        await self.session.commit()

        logger.info(
            "token_refreshed",
            platform=installation.platform,
            org_id=installation.external_org_id,
        )

        return tokens.access_token

    async def _update_last_used(self, installation: Installation) -> None:
        """Update last_used_at timestamp."""
        installation.last_used_at = datetime.utcnow()
        await self.session.commit()
```

### Webhook Routing by Installation

Update file: `agent-bot/api-gateway/webhooks/github/handler.py`

```python
async def route_webhook_to_installation(payload: dict[str, Any]) -> Installation | None:
    """Find the correct installation for a webhook."""
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        return None

    token_service = TokenService(get_session())
    query = select(Installation).where(
        Installation.platform == "github",
        Installation.external_install_id == str(installation_id),
        Installation.status == "active",
    )
    result = await get_session().execute(query)
    return result.scalar_one_or_none()
```

---

## 8. Migration Plan

### Phase 1: Database Setup (Day 1)

1. Create migration files
2. Run `alembic upgrade head`
3. Verify tables created

### Phase 2: OAuth Service (Days 2-3)

1. Create oauth-service container
2. Implement GitHub provider
3. Implement Slack provider
4. Implement Jira provider
5. Add to docker-compose.yml

### Phase 3: API Service Updates (Days 4-5)

1. Update github-api client for multi-tenant
2. Update slack-api client for multi-tenant
3. Update jira-api client for multi-tenant
4. Add fallback to env var tokens

### Phase 4: Webhook Updates (Day 6)

1. Update webhook handlers to include installation context
2. Route tasks to correct installation
3. Test end-to-end flow

### Phase 5: Testing & Rollout (Days 7-10)

1. Unit tests for OAuth flows
2. Integration tests with real apps
3. Documentation update
4. Production deployment

### Docker Compose Addition

```yaml
# Add to docker-compose.yml

oauth-service:
  build: ./oauth-service
  container_name: oauth-service
  ports:
    - "8010:8010"
  environment:
    - PORT=8010
    - DATABASE_URL=postgresql+asyncpg://agent:${POSTGRES_PASSWORD:-agent}@postgres:5432/agent_system
    - BASE_URL=${BASE_URL:-https://yourdomain.com}
    - GITHUB_APP_ID=${GITHUB_APP_ID}
    - GITHUB_APP_NAME=${GITHUB_APP_NAME}
    - GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
    - GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}
    - GITHUB_PRIVATE_KEY=${GITHUB_PRIVATE_KEY}
    - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
    - SLACK_CLIENT_ID=${SLACK_CLIENT_ID}
    - SLACK_CLIENT_SECRET=${SLACK_CLIENT_SECRET}
    - SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}
    - SLACK_STATE_SECRET=${SLACK_STATE_SECRET}
    - JIRA_CLIENT_ID=${JIRA_CLIENT_ID}
    - JIRA_CLIENT_SECRET=${JIRA_CLIENT_SECRET}
    - TOKEN_ENCRYPTION_KEY=${TOKEN_ENCRYPTION_KEY}
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - agent-network
  restart: unless-stopped
```

---

## 9. Security Considerations

### Token Encryption at Rest

```python
# services/encryption.py
from cryptography.fernet import Fernet
from config.settings import get_settings


class TokenEncryption:
    def __init__(self):
        settings = get_settings()
        self.fernet = Fernet(settings.token_encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

### Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Security Checklist

- [ ] Store tokens encrypted in database
- [ ] Use HTTPS for all OAuth redirects
- [ ] Validate webhook signatures before processing
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Log all token access and refresh events
- [ ] Set short token expiration where possible
- [ ] Implement token rotation for Slack (optional)
- [ ] Use PKCE for Jira OAuth (mandatory)
- [ ] Store webhook secrets per installation
- [ ] Never log full tokens (use truncation)

---

## Quick Reference: Environment Variables

```bash
# .env file additions for OAuth

# OAuth Service
BASE_URL=https://yourdomain.com
TOKEN_ENCRYPTION_KEY=your-fernet-key-here

# GitHub App
GITHUB_APP_ID=123456
GITHUB_APP_NAME=my-agent-bot
GITHUB_CLIENT_ID=Iv1.abc123
GITHUB_CLIENT_SECRET=abc123secret
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=webhook-secret-here

# Slack App
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=abc123secret
SLACK_SIGNING_SECRET=abc123signing
SLACK_STATE_SECRET=random-state-secret

# Jira OAuth
JIRA_CLIENT_ID=abc123-client-id
JIRA_CLIENT_SECRET=abc123-client-secret
```

---

## Summary

This guide provides a complete implementation plan for adding OAuth multi-tenant support to the agent-bot system. The key components are:

1. **Database Models** - Store installations with encrypted tokens
2. **OAuth Service** - Handle installation flows for all platforms
3. **Provider Implementations** - Platform-specific OAuth logic
4. **Token Service** - Manage token retrieval and refresh
5. **Multi-Tenant Routing** - Route requests to correct installation

The migration path allows gradual adoption while maintaining backward compatibility with existing env var-based tokens.
