import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

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
