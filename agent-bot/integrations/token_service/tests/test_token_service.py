import pytest
from datetime import datetime, timezone, timedelta
from token_service.models import Installation
from token_service.service import TokenService
from token_service.repository import InstallationRepository
from token_service.exceptions import (
    InstallationNotFoundError,
    TokenExpiredError,
)


@pytest.fixture
def repository() -> InstallationRepository:
    return InstallationRepository()


@pytest.fixture
def token_service(repository: InstallationRepository) -> TokenService:
    return TokenService(repository)


@pytest.fixture
def sample_installation() -> Installation:
    return Installation(
        id="inst_123",
        platform="github",
        organization_id="org_456",
        organization_name="Test Org",
        access_token="ghp_token123",
        refresh_token="refresh_token123",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["repo", "read:org"],
        webhook_secret="secret_abc",
        installed_at=datetime.now(timezone.utc),
        installed_by="user_789",
        metadata={"app_id": "12345"},
        is_active=True,
    )


@pytest.mark.asyncio
async def test_create_installation(
    token_service: TokenService, sample_installation: Installation
) -> None:
    await token_service.create_installation(sample_installation)
    retrieved = await token_service.get_installation(sample_installation.id)
    assert retrieved.id == sample_installation.id
    assert retrieved.organization_id == sample_installation.organization_id


@pytest.mark.asyncio
async def test_get_installation_not_found(token_service: TokenService) -> None:
    with pytest.raises(InstallationNotFoundError):
        await token_service.get_installation("nonexistent")


@pytest.mark.asyncio
async def test_get_valid_token_not_expired(
    token_service: TokenService, sample_installation: Installation
) -> None:
    await token_service.create_installation(sample_installation)
    token = await token_service.get_valid_token(sample_installation.id)
    assert token == sample_installation.access_token


@pytest.mark.asyncio
async def test_get_valid_token_expired_no_refresh(
    token_service: TokenService, sample_installation: Installation
) -> None:
    expired_installation = Installation(
        **{
            **sample_installation.model_dump(),
            "token_expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "refresh_token": None,
        }
    )
    await token_service.create_installation(expired_installation)

    with pytest.raises(TokenExpiredError):
        await token_service.get_valid_token(expired_installation.id)


@pytest.mark.asyncio
async def test_deactivate_installation(
    token_service: TokenService, sample_installation: Installation
) -> None:
    await token_service.create_installation(sample_installation)
    await token_service.deactivate_installation(sample_installation.id)

    retrieved = await token_service.get_installation(sample_installation.id)
    assert retrieved.is_active is False


@pytest.mark.asyncio
async def test_list_organization_installations(
    token_service: TokenService, sample_installation: Installation
) -> None:
    await token_service.create_installation(sample_installation)

    another_installation = Installation(
        **{
            **sample_installation.model_dump(),
            "id": "inst_456",
            "platform": "slack",
        }
    )
    await token_service.create_installation(another_installation)

    installations = await token_service.list_organization_installations(
        sample_installation.organization_id
    )
    assert len(installations) == 2
    assert all(inst.organization_id == sample_installation.organization_id for inst in installations)


@pytest.mark.asyncio
async def test_repository_get_by_organization(
    repository: InstallationRepository, sample_installation: Installation
) -> None:
    await repository.save(sample_installation)
    retrieved = await repository.get_by_organization(
        sample_installation.organization_id, "github"
    )
    assert retrieved.id == sample_installation.id


@pytest.mark.asyncio
async def test_repository_get_by_organization_not_found(
    repository: InstallationRepository,
) -> None:
    with pytest.raises(InstallationNotFoundError):
        await repository.get_by_organization("nonexistent_org", "github")
