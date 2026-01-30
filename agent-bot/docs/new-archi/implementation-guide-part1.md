# Agent Bot - TDD Implementation Guide

## Part 1: Foundation & Project Rules

---

## Strict Rules Reminder

Before ANY code, remember:

| Rule | Enforcement |
|------|-------------|
| **Max 300 lines per file** | Split into modules |
| **NO `any` types** | `ConfigDict(strict=True)` everywhere |
| **NO comments** | Self-explanatory code only |
| **Tests < 5 seconds** | Mock all external calls |
| **Structured logging** | `logger.info("event", key=value)` |
| **Async for I/O** | `httpx.AsyncClient`, not `requests` |

---

## TDD Workflow

```
1. Write failing test (RED)
2. Write minimal code to pass (GREEN)
3. Refactor while tests pass (REFACTOR)
4. Repeat
```

---

## Phase 1: Token Service Implementation

### Step 1.1: Create Directory Structure

```bash
mkdir -p integrations/token_service/token_service
mkdir -p integrations/token_service/tests
touch integrations/token_service/token_service/__init__.py
touch integrations/token_service/token_service/models.py
touch integrations/token_service/token_service/exceptions.py
touch integrations/token_service/token_service/repository.py
touch integrations/token_service/token_service/service.py
touch integrations/token_service/token_service/refresh.py
touch integrations/token_service/tests/__init__.py
touch integrations/token_service/tests/test_models.py
touch integrations/token_service/tests/test_repository.py
touch integrations/token_service/tests/test_service.py
touch integrations/token_service/pyproject.toml
```

### Step 1.2: Write Tests FIRST - Models

**File: `integrations/token_service/tests/test_models.py`** (< 100 lines)

```python
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    TokenInfo,
)


class TestPlatformEnum:
    def test_valid_platforms(self):
        assert Platform.GITHUB == "github"
        assert Platform.SLACK == "slack"
        assert Platform.JIRA == "jira"
        assert Platform.SENTRY == "sentry"

    def test_platform_from_string(self):
        assert Platform("github") == Platform.GITHUB


class TestInstallation:
    def test_create_valid_installation(self):
        now = datetime.now(timezone.utc)
        installation = Installation(
            id="inst-123",
            platform=Platform.GITHUB,
            organization_id="org-456",
            organization_name="My Org",
            access_token="gho_xxxx",
            refresh_token="ghr_xxxx",
            token_expires_at=now,
            scopes=["repo", "read:org"],
            webhook_secret="whsec_xxxx",
            installed_at=now,
            installed_by="user@example.com",
            is_active=True,
        )
        assert installation.id == "inst-123"
        assert installation.platform == Platform.GITHUB

    def test_reject_invalid_platform(self):
        with pytest.raises(ValidationError) as exc_info:
            Installation(
                id="inst-123",
                platform="invalid",
                organization_id="org-456",
                organization_name="My Org",
                access_token="token",
                webhook_secret="secret",
                installed_at=datetime.now(timezone.utc),
                installed_by="user@example.com",
                scopes=[],
                is_active=True,
            )
        assert "platform" in str(exc_info.value)

    def test_strict_mode_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            Installation(
                id="inst-123",
                platform="github",
                organization_id="org-456",
                organization_name="My Org",
                access_token="token",
                webhook_secret="secret",
                installed_at=datetime.now(timezone.utc),
                installed_by="user@example.com",
                scopes=[],
                is_active=True,
                extra_field="not_allowed",
            )


class TestInstallationCreate:
    def test_create_input_valid(self):
        create_input = InstallationCreate(
            platform=Platform.GITHUB,
            organization_id="org-456",
            organization_name="My Org",
            access_token="gho_xxxx",
            refresh_token="ghr_xxxx",
            token_expires_at=datetime.now(timezone.utc),
            scopes=["repo"],
            webhook_secret="whsec_xxxx",
            installed_by="user@example.com",
        )
        assert create_input.platform == Platform.GITHUB


class TestTokenInfo:
    def test_token_is_expired(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        token_info = TokenInfo(
            access_token="token",
            expires_at=past,
            scopes=["repo"],
        )
        assert token_info.is_expired is True

    def test_token_is_not_expired(self):
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        token_info = TokenInfo(
            access_token="token",
            expires_at=future,
            scopes=["repo"],
        )
        assert token_info.is_expired is False

    def test_token_without_expiry_is_not_expired(self):
        token_info = TokenInfo(
            access_token="token",
            expires_at=None,
            scopes=["repo"],
        )
        assert token_info.is_expired is False
```

### Step 1.3: Implement Models (Make Tests Pass)

**File: `integrations/token_service/token_service/models.py`** (< 150 lines)

```python
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Platform(str, Enum):
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    SENTRY = "sentry"


class Installation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str]
    webhook_secret: str
    installed_at: datetime
    installed_by: str
    metadata: dict[str, str] = Field(default_factory=dict)
    is_active: bool = True


class InstallationCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str]
    webhook_secret: str
    installed_by: str
    metadata: dict[str, str] = Field(default_factory=dict)


class InstallationUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str] | None = None
    is_active: bool | None = None
    metadata: dict[str, str] | None = None


class TokenInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    expires_at: datetime | None
    scopes: list[str]

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class InstallationFilter(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform | None = None
    organization_id: str | None = None
    is_active: bool | None = None
```

### Step 1.4: Write Tests FIRST - Exceptions

**File: `integrations/token_service/tests/test_exceptions.py`** (< 50 lines)

```python
import pytest
from token_service.exceptions import (
    TokenServiceError,
    InstallationNotFoundError,
    TokenExpiredError,
    TokenRefreshError,
)


class TestExceptions:
    def test_installation_not_found_error(self):
        error = InstallationNotFoundError(
            platform="github",
            organization_id="org-123",
        )
        assert "github" in str(error)
        assert "org-123" in str(error)

    def test_token_expired_error(self):
        error = TokenExpiredError(installation_id="inst-123")
        assert "inst-123" in str(error)

    def test_token_refresh_error(self):
        error = TokenRefreshError(
            installation_id="inst-123",
            reason="invalid_grant",
        )
        assert "inst-123" in str(error)
        assert "invalid_grant" in str(error)

    def test_inheritance(self):
        assert issubclass(InstallationNotFoundError, TokenServiceError)
        assert issubclass(TokenExpiredError, TokenServiceError)
        assert issubclass(TokenRefreshError, TokenServiceError)
```

### Step 1.5: Implement Exceptions

**File: `integrations/token_service/token_service/exceptions.py`** (< 60 lines)

```python
class TokenServiceError(Exception):
    pass


class InstallationNotFoundError(TokenServiceError):
    def __init__(self, platform: str, organization_id: str):
        self.platform = platform
        self.organization_id = organization_id
        super().__init__(
            f"Installation not found: platform={platform}, org={organization_id}"
        )


class TokenExpiredError(TokenServiceError):
    def __init__(self, installation_id: str):
        self.installation_id = installation_id
        super().__init__(f"Token expired for installation: {installation_id}")


class TokenRefreshError(TokenServiceError):
    def __init__(self, installation_id: str, reason: str):
        self.installation_id = installation_id
        self.reason = reason
        super().__init__(
            f"Token refresh failed for {installation_id}: {reason}"
        )


class DuplicateInstallationError(TokenServiceError):
    def __init__(self, platform: str, organization_id: str):
        self.platform = platform
        self.organization_id = organization_id
        super().__init__(
            f"Installation already exists: platform={platform}, org={organization_id}"
        )
```

### Step 1.6: Write Tests FIRST - Repository (Port)

**File: `integrations/token_service/tests/test_repository.py`** (< 150 lines)

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from token_service.repository import (
    InstallationRepositoryPort,
    InMemoryInstallationRepository,
)
from token_service.exceptions import (
    InstallationNotFoundError,
    DuplicateInstallationError,
)


@pytest.fixture
def sample_installation() -> Installation:
    return Installation(
        id="inst-123",
        platform=Platform.GITHUB,
        organization_id="org-456",
        organization_name="Test Org",
        access_token="gho_xxxx",
        refresh_token="ghr_xxxx",
        token_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        scopes=["repo", "read:org"],
        webhook_secret="whsec_xxxx",
        installed_at=datetime.now(timezone.utc),
        installed_by="user@test.com",
        is_active=True,
    )


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


class TestInMemoryRepository:
    @pytest.fixture
    def repository(self) -> InMemoryInstallationRepository:
        return InMemoryInstallationRepository()

    @pytest.mark.asyncio
    async def test_create_installation(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        installation = await repository.create(sample_create_input)
        
        assert installation.id is not None
        assert installation.platform == Platform.GITHUB
        assert installation.organization_id == "org-456"

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_error(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        await repository.create(sample_create_input)
        
        with pytest.raises(DuplicateInstallationError):
            await repository.create(sample_create_input)

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        created = await repository.create(sample_create_input)
        fetched = await repository.get_by_id(created.id)
        
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: InMemoryInstallationRepository,
    ):
        result = await repository.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_platform_and_org(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        await repository.create(sample_create_input)
        
        fetched = await repository.get_by_platform_and_org(
            platform=Platform.GITHUB,
            organization_id="org-456",
        )
        
        assert fetched is not None
        assert fetched.platform == Platform.GITHUB

    @pytest.mark.asyncio
    async def test_update_installation(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        created = await repository.create(sample_create_input)
        
        update = InstallationUpdate(access_token="new_token")
        updated = await repository.update(created.id, update)
        
        assert updated.access_token == "new_token"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises_error(
        self,
        repository: InMemoryInstallationRepository,
    ):
        update = InstallationUpdate(access_token="new_token")
        
        with pytest.raises(InstallationNotFoundError):
            await repository.update("nonexistent", update)

    @pytest.mark.asyncio
    async def test_find_by_filter(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        await repository.create(sample_create_input)
        
        results = await repository.find(
            InstallationFilter(platform=Platform.GITHUB)
        )
        
        assert len(results) == 1
        assert results[0].platform == Platform.GITHUB

    @pytest.mark.asyncio
    async def test_delete_installation(
        self,
        repository: InMemoryInstallationRepository,
        sample_create_input: InstallationCreate,
    ):
        created = await repository.create(sample_create_input)
        
        deleted = await repository.delete(created.id)
        assert deleted is True
        
        fetched = await repository.get_by_id(created.id)
        assert fetched is None
```

### Step 1.7: Implement Repository Port & In-Memory Adapter

**File: `integrations/token_service/token_service/repository.py`** (< 150 lines)

```python
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from .models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from .exceptions import (
    InstallationNotFoundError,
    DuplicateInstallationError,
)


class InstallationRepositoryPort(Protocol):
    async def create(self, data: InstallationCreate) -> Installation: ...
    async def get_by_id(self, installation_id: str) -> Installation | None: ...
    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None: ...
    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation: ...
    async def find(self, filter_: InstallationFilter) -> list[Installation]: ...
    async def delete(self, installation_id: str) -> bool: ...


class InMemoryInstallationRepository:
    def __init__(self) -> None:
        self._storage: dict[str, Installation] = {}

    async def create(self, data: InstallationCreate) -> Installation:
        existing = await self.get_by_platform_and_org(
            data.platform, data.organization_id
        )
        if existing:
            raise DuplicateInstallationError(
                data.platform.value, data.organization_id
            )

        installation = Installation(
            id=f"inst-{uuid4().hex[:12]}",
            platform=data.platform,
            organization_id=data.organization_id,
            organization_name=data.organization_name,
            access_token=data.access_token,
            refresh_token=data.refresh_token,
            token_expires_at=data.token_expires_at,
            scopes=data.scopes,
            webhook_secret=data.webhook_secret,
            installed_at=datetime.now(timezone.utc),
            installed_by=data.installed_by,
            metadata=data.metadata,
            is_active=True,
        )
        self._storage[installation.id] = installation
        return installation

    async def get_by_id(self, installation_id: str) -> Installation | None:
        return self._storage.get(installation_id)

    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None:
        for installation in self._storage.values():
            if (
                installation.platform == platform
                and installation.organization_id == organization_id
            ):
                return installation
        return None

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation:
        existing = self._storage.get(installation_id)
        if not existing:
            raise InstallationNotFoundError("unknown", installation_id)

        update_data = data.model_dump(exclude_unset=True)
        updated = existing.model_copy(update=update_data)
        self._storage[installation_id] = updated
        return updated

    async def find(self, filter_: InstallationFilter) -> list[Installation]:
        results: list[Installation] = []
        for installation in self._storage.values():
            if self._matches_filter(installation, filter_):
                results.append(installation)
        return results

    async def delete(self, installation_id: str) -> bool:
        if installation_id in self._storage:
            del self._storage[installation_id]
            return True
        return False

    def _matches_filter(
        self, installation: Installation, filter_: InstallationFilter
    ) -> bool:
        if filter_.platform and installation.platform != filter_.platform:
            return False
        if filter_.organization_id and installation.organization_id != filter_.organization_id:
            return False
        if filter_.is_active is not None and installation.is_active != filter_.is_active:
            return False
        return True
```

### Step 1.8: Write Tests FIRST - Service

**File: `integrations/token_service/tests/test_service.py`** (< 200 lines)

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    TokenInfo,
)
from token_service.service import TokenService
from token_service.repository import InMemoryInstallationRepository
from token_service.exceptions import (
    InstallationNotFoundError,
    TokenExpiredError,
)


@pytest.fixture
def repository() -> InMemoryInstallationRepository:
    return InMemoryInstallationRepository()


@pytest.fixture
def mock_refresh_handler() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    repository: InMemoryInstallationRepository,
    mock_refresh_handler: AsyncMock,
) -> TokenService:
    return TokenService(
        repository=repository,
        refresh_handlers={Platform.GITHUB: mock_refresh_handler},
    )


@pytest.fixture
def sample_create_input() -> InstallationCreate:
    return InstallationCreate(
        platform=Platform.GITHUB,
        organization_id="org-456",
        organization_name="Test Org",
        access_token="gho_xxxx",
        refresh_token="ghr_xxxx",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["repo"],
        webhook_secret="whsec_xxxx",
        installed_by="user@test.com",
    )


class TestTokenServiceCreate:
    @pytest.mark.asyncio
    async def test_create_installation(
        self,
        service: TokenService,
        sample_create_input: InstallationCreate,
    ):
        installation = await service.create_installation(sample_create_input)
        
        assert installation.platform == Platform.GITHUB
        assert installation.organization_id == "org-456"


class TestTokenServiceGetToken:
    @pytest.mark.asyncio
    async def test_get_valid_token(
        self,
        service: TokenService,
        sample_create_input: InstallationCreate,
    ):
        await service.create_installation(sample_create_input)
        
        token_info = await service.get_token(
            platform=Platform.GITHUB,
            organization_id="org-456",
        )
        
        assert token_info.access_token == "gho_xxxx"
        assert token_info.is_expired is False

    @pytest.mark.asyncio
    async def test_get_token_not_found(
        self,
        service: TokenService,
    ):
        with pytest.raises(InstallationNotFoundError):
            await service.get_token(
                platform=Platform.GITHUB,
                organization_id="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_get_expired_token_triggers_refresh(
        self,
        service: TokenService,
        repository: InMemoryInstallationRepository,
        mock_refresh_handler: AsyncMock,
    ):
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        create_input = InstallationCreate(
            platform=Platform.GITHUB,
            organization_id="org-456",
            organization_name="Test Org",
            access_token="old_token",
            refresh_token="ghr_xxxx",
            token_expires_at=expired_time,
            scopes=["repo"],
            webhook_secret="whsec_xxxx",
            installed_by="user@test.com",
        )
        await service.create_installation(create_input)

        mock_refresh_handler.return_value = TokenInfo(
            access_token="new_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["repo"],
        )

        token_info = await service.get_token(
            platform=Platform.GITHUB,
            organization_id="org-456",
        )

        mock_refresh_handler.assert_called_once()
        assert token_info.access_token == "new_token"


class TestTokenServiceGetWebhookSecret:
    @pytest.mark.asyncio
    async def test_get_webhook_secret(
        self,
        service: TokenService,
        sample_create_input: InstallationCreate,
    ):
        await service.create_installation(sample_create_input)
        
        secret = await service.get_webhook_secret(
            platform=Platform.GITHUB,
            organization_id="org-456",
        )
        
        assert secret == "whsec_xxxx"

    @pytest.mark.asyncio
    async def test_get_webhook_secret_not_found(
        self,
        service: TokenService,
    ):
        with pytest.raises(InstallationNotFoundError):
            await service.get_webhook_secret(
                platform=Platform.GITHUB,
                organization_id="nonexistent",
            )


class TestTokenServiceDeactivate:
    @pytest.mark.asyncio
    async def test_deactivate_installation(
        self,
        service: TokenService,
        sample_create_input: InstallationCreate,
    ):
        installation = await service.create_installation(sample_create_input)
        
        deactivated = await service.deactivate_installation(installation.id)
        
        assert deactivated.is_active is False
```

### Step 1.9: Implement Service

**File: `integrations/token_service/token_service/service.py`** (< 150 lines)

```python
from datetime import datetime, timezone
from typing import Callable, Awaitable
import structlog

from .models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    TokenInfo,
)
from .repository import InstallationRepositoryPort
from .exceptions import (
    InstallationNotFoundError,
    TokenExpiredError,
)

logger = structlog.get_logger()

RefreshHandler = Callable[[Installation], Awaitable[TokenInfo]]


class TokenService:
    def __init__(
        self,
        repository: InstallationRepositoryPort,
        refresh_handlers: dict[Platform, RefreshHandler] | None = None,
    ) -> None:
        self._repository = repository
        self._refresh_handlers = refresh_handlers or {}

    async def create_installation(
        self, data: InstallationCreate
    ) -> Installation:
        logger.info(
            "creating_installation",
            platform=data.platform.value,
            organization_id=data.organization_id,
        )
        installation = await self._repository.create(data)
        logger.info(
            "installation_created",
            installation_id=installation.id,
            platform=data.platform.value,
        )
        return installation

    async def get_token(
        self,
        platform: Platform,
        organization_id: str,
    ) -> TokenInfo:
        installation = await self._get_installation(platform, organization_id)
        
        token_info = TokenInfo(
            access_token=installation.access_token,
            expires_at=installation.token_expires_at,
            scopes=installation.scopes,
        )

        if token_info.is_expired:
            logger.info(
                "token_expired_refreshing",
                installation_id=installation.id,
            )
            token_info = await self._refresh_token(installation)

        return token_info

    async def get_webhook_secret(
        self,
        platform: Platform,
        organization_id: str,
    ) -> str:
        installation = await self._get_installation(platform, organization_id)
        return installation.webhook_secret

    async def get_installation_by_id(
        self, installation_id: str
    ) -> Installation | None:
        return await self._repository.get_by_id(installation_id)

    async def deactivate_installation(
        self, installation_id: str
    ) -> Installation:
        logger.info("deactivating_installation", installation_id=installation_id)
        update = InstallationUpdate(is_active=False)
        return await self._repository.update(installation_id, update)

    async def _get_installation(
        self,
        platform: Platform,
        organization_id: str,
    ) -> Installation:
        installation = await self._repository.get_by_platform_and_org(
            platform, organization_id
        )
        if not installation:
            raise InstallationNotFoundError(platform.value, organization_id)
        if not installation.is_active:
            raise InstallationNotFoundError(platform.value, organization_id)
        return installation

    async def _refresh_token(self, installation: Installation) -> TokenInfo:
        handler = self._refresh_handlers.get(installation.platform)
        if not handler:
            raise TokenExpiredError(installation.id)

        new_token_info = await handler(installation)

        await self._repository.update(
            installation.id,
            InstallationUpdate(
                access_token=new_token_info.access_token,
                token_expires_at=new_token_info.expires_at,
            ),
        )

        logger.info(
            "token_refreshed",
            installation_id=installation.id,
        )

        return new_token_info
```

### Step 1.10: Create Package Init

**File: `integrations/token_service/token_service/__init__.py`** (< 30 lines)

```python
from .models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
    TokenInfo,
)
from .service import TokenService
from .repository import (
    InstallationRepositoryPort,
    InMemoryInstallationRepository,
)
from .exceptions import (
    TokenServiceError,
    InstallationNotFoundError,
    TokenExpiredError,
    TokenRefreshError,
    DuplicateInstallationError,
)

__all__ = [
    "Platform",
    "Installation",
    "InstallationCreate",
    "InstallationUpdate",
    "InstallationFilter",
    "TokenInfo",
    "TokenService",
    "InstallationRepositoryPort",
    "InMemoryInstallationRepository",
    "TokenServiceError",
    "InstallationNotFoundError",
    "TokenExpiredError",
    "TokenRefreshError",
    "DuplicateInstallationError",
]
```

### Step 1.11: Create pyproject.toml

**File: `integrations/token_service/pyproject.toml`**

```toml
[project]
name = "token-service"
version = "0.1.0"
description = "Multi-organization token management service"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "structlog>=23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
strict = true
python_version = "3.11"
```

---

## Run Tests to Verify

```bash
cd integrations/token_service
pip install -e ".[dev]"
pytest -v --tb=short

# Expected output:
# tests/test_models.py::TestPlatformEnum::test_valid_platforms PASSED
# tests/test_models.py::TestPlatformEnum::test_platform_from_string PASSED
# tests/test_models.py::TestInstallation::test_create_valid_installation PASSED
# ... all tests pass
```

---

## Checkpoint 1 Complete ✅

Before proceeding, verify:
- [ ] All files < 300 lines
- [ ] NO `any` types used
- [ ] NO comments in code
- [ ] All tests pass (< 5 seconds)
- [ ] Structured logging used

Continue to Part 2 for PostgreSQL Repository Adapter...
