# Agent Bot - TDD Implementation Guide

## Part 2: PostgreSQL Adapter & OAuth Handlers

---

## Phase 2: PostgreSQL Repository Adapter

### Step 2.1: Create Directory Structure

```bash
mkdir -p integrations/token_service/token_service/adapters
touch integrations/token_service/token_service/adapters/__init__.py
touch integrations/token_service/token_service/adapters/postgres.py
touch integrations/token_service/tests/test_postgres_repository.py
```

### Step 2.2: Write Tests FIRST - PostgreSQL Repository

**File: `integrations/token_service/tests/test_postgres_repository.py`** (< 200 lines)

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from token_service.adapters.postgres import PostgresInstallationRepository
from token_service.exceptions import (
    InstallationNotFoundError,
    DuplicateInstallationError,
)


@pytest.fixture
def mock_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    return pool


@pytest.fixture
def sample_create_input() -> InstallationCreate:
    return InstallationCreate(
        platform=Platform.GITHUB,
        organization_id="org-456",
        organization_name="Test Org",
        access_token="gho_xxxx",
        refresh_token="ghr_xxxx",
        token_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        scopes=["repo", "read:org"],
        webhook_secret="whsec_xxxx",
        installed_by="user@test.com",
    )


@pytest.fixture
def sample_db_row() -> dict:
    return {
        "id": "inst-123",
        "platform": "github",
        "organization_id": "org-456",
        "organization_name": "Test Org",
        "access_token": "gho_xxxx",
        "refresh_token": "ghr_xxxx",
        "token_expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
        "scopes": ["repo", "read:org"],
        "webhook_secret": "whsec_xxxx",
        "installed_at": datetime.now(timezone.utc),
        "installed_by": "user@test.com",
        "metadata": {},
        "is_active": True,
    }


class TestPostgresRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_installation_success(
        self,
        mock_pool: AsyncMock,
        sample_create_input: InstallationCreate,
        sample_db_row: dict,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=sample_db_row)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        installation = await repository.create(sample_create_input)

        assert installation.platform == Platform.GITHUB
        assert installation.organization_id == "org-456"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_error(
        self,
        mock_pool: AsyncMock,
        sample_create_input: InstallationCreate,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            side_effect=Exception("unique_violation")
        )
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)

        with pytest.raises(DuplicateInstallationError):
            await repository.create(sample_create_input)


class TestPostgresRepositoryGet:
    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        mock_pool: AsyncMock,
        sample_db_row: dict,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=sample_db_row)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        installation = await repository.get_by_id("inst-123")

        assert installation is not None
        assert installation.id == "inst-123"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        mock_pool: AsyncMock,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        installation = await repository.get_by_id("nonexistent")

        assert installation is None

    @pytest.mark.asyncio
    async def test_get_by_platform_and_org(
        self,
        mock_pool: AsyncMock,
        sample_db_row: dict,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=sample_db_row)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        installation = await repository.get_by_platform_and_org(
            Platform.GITHUB, "org-456"
        )

        assert installation is not None
        assert installation.platform == Platform.GITHUB


class TestPostgresRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_success(
        self,
        mock_pool: AsyncMock,
        sample_db_row: dict,
    ):
        updated_row = {**sample_db_row, "access_token": "new_token"}
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=updated_row)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        update = InstallationUpdate(access_token="new_token")
        installation = await repository.update("inst-123", update)

        assert installation.access_token == "new_token"

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        mock_pool: AsyncMock,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        update = InstallationUpdate(access_token="new_token")

        with pytest.raises(InstallationNotFoundError):
            await repository.update("nonexistent", update)


class TestPostgresRepositoryFind:
    @pytest.mark.asyncio
    async def test_find_by_filter(
        self,
        mock_pool: AsyncMock,
        sample_db_row: dict,
    ):
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[sample_db_row])
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        filter_ = InstallationFilter(platform=Platform.GITHUB)
        installations = await repository.find(filter_)

        assert len(installations) == 1
        assert installations[0].platform == Platform.GITHUB


class TestPostgresRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        mock_pool: AsyncMock,
    ):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        result = await repository.delete("inst-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        mock_pool: AsyncMock,
    ):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 0")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        repository = PostgresInstallationRepository(mock_pool)
        result = await repository.delete("nonexistent")

        assert result is False
```

### Step 2.3: Implement PostgreSQL Repository

**File: `integrations/token_service/token_service/adapters/postgres.py`** (< 200 lines)

```python
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import json

import asyncpg
import structlog

from ..models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from ..exceptions import (
    InstallationNotFoundError,
    DuplicateInstallationError,
)

logger = structlog.get_logger()

INSERT_QUERY = """
    INSERT INTO installations (
        id, platform, organization_id, organization_name,
        access_token, refresh_token, token_expires_at,
        scopes, webhook_secret, installed_at, installed_by,
        metadata, is_active
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
    )
    RETURNING *
"""

SELECT_BY_ID_QUERY = """
    SELECT * FROM installations WHERE id = $1
"""

SELECT_BY_PLATFORM_ORG_QUERY = """
    SELECT * FROM installations 
    WHERE platform = $1 AND organization_id = $2
"""

DELETE_QUERY = """
    DELETE FROM installations WHERE id = $1
"""


class PostgresInstallationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, data: InstallationCreate) -> Installation:
        installation_id = f"inst-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    INSERT_QUERY,
                    installation_id,
                    data.platform.value,
                    data.organization_id,
                    data.organization_name,
                    data.access_token,
                    data.refresh_token,
                    data.token_expires_at,
                    data.scopes,
                    data.webhook_secret,
                    now,
                    data.installed_by,
                    json.dumps(data.metadata),
                    True,
                )
        except Exception as e:
            if "unique_violation" in str(e):
                raise DuplicateInstallationError(
                    data.platform.value, data.organization_id
                )
            raise

        return self._row_to_installation(row)

    async def get_by_id(self, installation_id: str) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(SELECT_BY_ID_QUERY, installation_id)

        if row is None:
            return None

        return self._row_to_installation(row)

    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                SELECT_BY_PLATFORM_ORG_QUERY,
                platform.value,
                organization_id,
            )

        if row is None:
            return None

        return self._row_to_installation(row)

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation:
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            existing = await self.get_by_id(installation_id)
            if existing is None:
                raise InstallationNotFoundError("unknown", installation_id)
            return existing

        set_clauses = []
        values = []
        for i, (key, value) in enumerate(update_fields.items(), start=1):
            set_clauses.append(f"{key} = ${i}")
            values.append(value)

        values.append(installation_id)
        query = f"""
            UPDATE installations 
            SET {", ".join(set_clauses)}
            WHERE id = ${len(values)}
            RETURNING *
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)

        if row is None:
            raise InstallationNotFoundError("unknown", installation_id)

        return self._row_to_installation(row)

    async def find(self, filter_: InstallationFilter) -> list[Installation]:
        conditions = []
        values = []
        param_index = 1

        if filter_.platform:
            conditions.append(f"platform = ${param_index}")
            values.append(filter_.platform.value)
            param_index += 1

        if filter_.organization_id:
            conditions.append(f"organization_id = ${param_index}")
            values.append(filter_.organization_id)
            param_index += 1

        if filter_.is_active is not None:
            conditions.append(f"is_active = ${param_index}")
            values.append(filter_.is_active)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT * FROM installations WHERE {where_clause}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *values)

        return [self._row_to_installation(row) for row in rows]

    async def delete(self, installation_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(DELETE_QUERY, installation_id)

        return result == "DELETE 1"

    def _row_to_installation(self, row: asyncpg.Record) -> Installation:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Installation(
            id=row["id"],
            platform=Platform(row["platform"]),
            organization_id=row["organization_id"],
            organization_name=row["organization_name"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            token_expires_at=row["token_expires_at"],
            scopes=row["scopes"],
            webhook_secret=row["webhook_secret"],
            installed_at=row["installed_at"],
            installed_by=row["installed_by"],
            metadata=metadata,
            is_active=row["is_active"],
        )
```

---

## Phase 3: OAuth Handlers

### Step 3.1: Create Directory Structure

```bash
mkdir -p api-gateway/oauth
touch api-gateway/oauth/__init__.py
touch api-gateway/oauth/models.py
touch api-gateway/oauth/github.py
touch api-gateway/oauth/router.py
mkdir -p api-gateway/tests/oauth
touch api-gateway/tests/oauth/__init__.py
touch api-gateway/tests/oauth/test_models.py
touch api-gateway/tests/oauth/test_github.py
```

### Step 3.2: Write Tests FIRST - OAuth Models

**File: `api-gateway/tests/oauth/test_models.py`** (< 80 lines)

```python
import pytest
from pydantic import ValidationError

from oauth.models import (
    OAuthState,
    OAuthCallbackParams,
    GitHubTokenResponse,
    GitHubInstallationInfo,
)


class TestOAuthState:
    def test_create_valid_state(self):
        state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        assert state.platform == "github"

    def test_to_encoded_string(self):
        state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        encoded = state.to_encoded()
        assert isinstance(encoded, str)

    def test_from_encoded_string(self):
        state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        encoded = state.to_encoded()
        decoded = OAuthState.from_encoded(encoded)
        assert decoded.platform == state.platform
        assert decoded.nonce == state.nonce


class TestOAuthCallbackParams:
    def test_valid_callback_params(self):
        params = OAuthCallbackParams(
            code="auth_code_123",
            state="encoded_state",
        )
        assert params.code == "auth_code_123"

    def test_reject_missing_code(self):
        with pytest.raises(ValidationError):
            OAuthCallbackParams(state="encoded_state")


class TestGitHubTokenResponse:
    def test_valid_token_response(self):
        response = GitHubTokenResponse(
            access_token="gho_xxxx",
            token_type="bearer",
            scope="repo,read:org",
        )
        assert response.access_token == "gho_xxxx"
        assert response.scopes == ["repo", "read:org"]

    def test_scopes_from_string(self):
        response = GitHubTokenResponse(
            access_token="gho_xxxx",
            token_type="bearer",
            scope="repo,read:org,user",
        )
        assert len(response.scopes) == 3


class TestGitHubInstallationInfo:
    def test_valid_installation_info(self):
        info = GitHubInstallationInfo(
            installation_id=12345,
            account_id=67890,
            account_login="my-org",
            account_type="Organization",
        )
        assert info.installation_id == 12345
        assert info.account_login == "my-org"
```

### Step 3.3: Implement OAuth Models

**File: `api-gateway/oauth/models.py`** (< 120 lines)

```python
import base64
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OAuthState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Literal["github", "slack", "jira"]
    redirect_uri: str
    nonce: str
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_encoded(self) -> str:
        json_str = self.model_dump_json()
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @classmethod
    def from_encoded(cls, encoded: str) -> "OAuthState":
        json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
        return cls.model_validate_json(json_str)


class OAuthCallbackParams(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    code: str
    state: str
    error: str | None = None
    error_description: str | None = None


class OAuthError(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    error: str
    error_description: str


class GitHubTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    token_type: str
    scope: str
    refresh_token: str | None = None
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None

    @computed_field
    @property
    def scopes(self) -> list[str]:
        return [s.strip() for s in self.scope.split(",") if s.strip()]


class GitHubInstallationInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    installation_id: int
    account_id: int
    account_login: str
    account_type: Literal["User", "Organization"]
    permissions: dict[str, str] = Field(default_factory=dict)


class GitHubAppInstallationToken(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    token: str
    expires_at: str
    permissions: dict[str, str]
    repository_selection: Literal["all", "selected"]


class SlackTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    ok: bool
    access_token: str
    token_type: Literal["bot"]
    scope: str
    bot_user_id: str
    app_id: str
    team: dict[str, str]
    authed_user: dict[str, str]

    @computed_field
    @property
    def scopes(self) -> list[str]:
        return [s.strip() for s in self.scope.split(",") if s.strip()]

    @computed_field
    @property
    def team_id(self) -> str:
        return self.team.get("id", "")

    @computed_field
    @property
    def team_name(self) -> str:
        return self.team.get("name", "")


class JiraTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: str | None = None

    @computed_field
    @property
    def scopes(self) -> list[str]:
        return [s.strip() for s in self.scope.split(" ") if s.strip()]
```

### Step 3.4: Write Tests FIRST - GitHub OAuth Handler

**File: `api-gateway/tests/oauth/test_github.py`** (< 200 lines)

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from oauth.github import GitHubOAuthHandler
from oauth.models import OAuthState, OAuthCallbackParams, GitHubTokenResponse


@pytest.fixture
def github_config() -> dict[str, str]:
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "app_id": "123456",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def handler(
    github_config: dict[str, str],
    mock_http_client: AsyncMock,
) -> GitHubOAuthHandler:
    return GitHubOAuthHandler(
        client_id=github_config["client_id"],
        client_secret=github_config["client_secret"],
        http_client=mock_http_client,
    )


class TestGitHubOAuthHandlerAuthUrl:
    def test_generate_auth_url(self, handler: GitHubOAuthHandler):
        state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        
        url = handler.get_authorization_url(state)
        
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=test_client_id" in url
        assert "state=" in url

    def test_auth_url_includes_scopes(self, handler: GitHubOAuthHandler):
        state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        
        url = handler.get_authorization_url(
            state,
            scopes=["repo", "read:org"],
        )
        
        assert "scope=repo" in url or "scope=repo%2Cread%3Aorg" in url


class TestGitHubOAuthHandlerExchangeCode:
    @pytest.mark.asyncio
    async def test_exchange_code_success(
        self,
        handler: GitHubOAuthHandler,
        mock_http_client: AsyncMock,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_xxxx",
            "token_type": "bearer",
            "scope": "repo,read:org",
        }
        mock_http_client.post.return_value = mock_response

        token_response = await handler.exchange_code("auth_code_123")

        assert token_response.access_token == "gho_xxxx"
        assert token_response.scopes == ["repo", "read:org"]

    @pytest.mark.asyncio
    async def test_exchange_code_failure(
        self,
        handler: GitHubOAuthHandler,
        mock_http_client: AsyncMock,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect",
        }
        mock_http_client.post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            await handler.exchange_code("invalid_code")
        
        assert "bad_verification_code" in str(exc_info.value)


class TestGitHubOAuthHandlerGetInstallation:
    @pytest.mark.asyncio
    async def test_get_installation_info(
        self,
        handler: GitHubOAuthHandler,
        mock_http_client: AsyncMock,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "account": {
                "id": 67890,
                "login": "my-org",
                "type": "Organization",
            },
            "permissions": {"contents": "read", "pull_requests": "write"},
        }
        mock_http_client.get.return_value = mock_response

        info = await handler.get_installation_info(
            installation_id=12345,
            access_token="gho_xxxx",
        )

        assert info.installation_id == 12345
        assert info.account_login == "my-org"


class TestGitHubOAuthHandlerValidateState:
    def test_validate_state_success(self, handler: GitHubOAuthHandler):
        original_state = OAuthState(
            platform="github",
            redirect_uri="https://app.example.com/callback",
            nonce="abc123",
        )
        encoded = original_state.to_encoded()

        decoded = handler.validate_state(encoded)

        assert decoded.platform == "github"
        assert decoded.nonce == "abc123"

    def test_validate_state_invalid(self, handler: GitHubOAuthHandler):
        with pytest.raises(ValueError):
            handler.validate_state("invalid_base64_state")


class TestGitHubOAuthHandlerGenerateWebhookSecret:
    def test_generate_webhook_secret(self, handler: GitHubOAuthHandler):
        secret = handler.generate_webhook_secret()
        
        assert len(secret) == 64
        assert secret.isalnum()
```

### Step 3.5: Implement GitHub OAuth Handler

**File: `api-gateway/oauth/github.py`** (< 180 lines)

```python
import secrets
from urllib.parse import urlencode

import httpx
import structlog

from .models import (
    OAuthState,
    OAuthError,
    GitHubTokenResponse,
    GitHubInstallationInfo,
)

logger = structlog.get_logger()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class GitHubOAuthError(Exception):
    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}")


class GitHubOAuthHandler:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http_client = http_client

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: list[str] | None = None,
    ) -> str:
        default_scopes = ["repo", "read:org", "read:user"]
        final_scopes = scopes or default_scopes

        params = {
            "client_id": self._client_id,
            "redirect_uri": state.redirect_uri,
            "scope": ",".join(final_scopes),
            "state": state.to_encoded(),
        }

        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GitHubTokenResponse:
        logger.info("exchanging_github_code")

        client = self._get_client()
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()

        if response.status_code != 200 or "error" in data:
            error = data.get("error", "unknown_error")
            description = data.get("error_description", "Unknown error")
            logger.error(
                "github_code_exchange_failed",
                error=error,
                description=description,
            )
            raise GitHubOAuthError(error, description)

        logger.info("github_code_exchanged_successfully")
        return GitHubTokenResponse.model_validate(data)

    async def get_installation_info(
        self,
        installation_id: int,
        access_token: str,
    ) -> GitHubInstallationInfo:
        logger.info(
            "fetching_github_installation",
            installation_id=installation_id,
        )

        client = self._get_client()
        response = await client.get(
            f"{GITHUB_API_URL}/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if response.status_code != 200:
            raise GitHubOAuthError(
                "installation_fetch_failed",
                f"Failed to fetch installation: {response.status_code}",
            )

        data = response.json()
        return GitHubInstallationInfo(
            installation_id=data["id"],
            account_id=data["account"]["id"],
            account_login=data["account"]["login"],
            account_type=data["account"]["type"],
            permissions=data.get("permissions", {}),
        )

    async def get_authenticated_user(
        self, access_token: str
    ) -> dict[str, str]:
        client = self._get_client()
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if response.status_code != 200:
            raise GitHubOAuthError(
                "user_fetch_failed",
                f"Failed to fetch user: {response.status_code}",
            )

        data = response.json()
        return {
            "id": str(data["id"]),
            "login": data["login"],
            "email": data.get("email", ""),
        }

    def validate_state(self, encoded_state: str) -> OAuthState:
        try:
            return OAuthState.from_encoded(encoded_state)
        except Exception as e:
            logger.error("invalid_oauth_state", error=str(e))
            raise ValueError("Invalid OAuth state")

    def generate_webhook_secret(self) -> str:
        return secrets.token_hex(32)

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client:
            return self._http_client
        return httpx.AsyncClient()
```

### Step 3.6: Create OAuth Router

**File: `api-gateway/oauth/router.py`** (< 150 lines)

```python
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
import structlog

from .models import OAuthState, OAuthCallbackParams
from .github import GitHubOAuthHandler, GitHubOAuthError
from token_service import (
    TokenService,
    InstallationCreate,
    Platform,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/oauth", tags=["oauth"])


class OAuthConfig:
    def __init__(
        self,
        github_client_id: str,
        github_client_secret: str,
        base_url: str,
    ) -> None:
        self.github_client_id = github_client_id
        self.github_client_secret = github_client_secret
        self.base_url = base_url


def get_github_handler(config: OAuthConfig) -> GitHubOAuthHandler:
    return GitHubOAuthHandler(
        client_id=config.github_client_id,
        client_secret=config.github_client_secret,
    )


@router.get("/github/authorize")
async def github_authorize(
    redirect_uri: str = Query(..., description="Post-install redirect"),
    handler: GitHubOAuthHandler = Depends(get_github_handler),
) -> RedirectResponse:
    state = OAuthState(
        platform="github",
        redirect_uri=redirect_uri,
        nonce=secrets.token_urlsafe(16),
    )

    auth_url = handler.get_authorization_url(state)
    logger.info("redirecting_to_github_oauth", redirect_uri=redirect_uri)

    return RedirectResponse(url=auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    handler: GitHubOAuthHandler = Depends(get_github_handler),
    token_service: TokenService = Depends(),
) -> dict[str, str]:
    try:
        oauth_state = handler.validate_state(state)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    try:
        token_response = await handler.exchange_code(code)
    except GitHubOAuthError as e:
        logger.error("github_oauth_failed", error=e.error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth failed: {e.description}",
        )

    user_info = await handler.get_authenticated_user(token_response.access_token)

    installation_data = InstallationCreate(
        platform=Platform.GITHUB,
        organization_id=user_info["id"],
        organization_name=user_info["login"],
        access_token=token_response.access_token,
        refresh_token=token_response.refresh_token,
        scopes=token_response.scopes,
        webhook_secret=handler.generate_webhook_secret(),
        installed_by=user_info.get("email", user_info["login"]),
    )

    installation = await token_service.create_installation(installation_data)

    logger.info(
        "github_installation_created",
        installation_id=installation.id,
        organization=user_info["login"],
    )

    return {
        "status": "success",
        "installation_id": installation.id,
        "organization": user_info["login"],
        "webhook_secret": installation.webhook_secret,
        "redirect_uri": oauth_state.redirect_uri,
    }
```

---

## Run Tests to Verify Phase 2-3

```bash
# Token Service Tests
cd integrations/token_service
pytest -v tests/test_postgres_repository.py

# OAuth Tests
cd api-gateway
pytest -v tests/oauth/

# Expected: All tests pass < 5 seconds
```

---

## Checkpoint 2 Complete ✅

Before proceeding, verify:
- [ ] All files < 300 lines
- [ ] NO `any` types used
- [ ] NO comments in code
- [ ] All tests pass (< 5 seconds)
- [ ] Structured logging used
- [ ] Async for all I/O

Continue to Part 3 for Ports & Adapters Pattern...
