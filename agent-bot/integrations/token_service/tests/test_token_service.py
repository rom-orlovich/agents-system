import pytest
from datetime import datetime, timezone, timedelta
from token_service import (
    TokenService,
    MemoryInstallationRepository,
    CreateInstallationInput,
    InstallationNotFoundError,
    InstallationInactiveError,
    TokenExpiredError,
)


@pytest.fixture
def repository():
    return MemoryInstallationRepository()


@pytest.fixture
def service(repository):
    return TokenService(repository)


@pytest.fixture
def github_install_data():
    return CreateInstallationInput(
        platform="github",
        organization_id="org-123",
        organization_name="Test Org",
        access_token="gho_test_token_123",
        refresh_token="gho_refresh_123",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["repo", "issues"],
        webhook_secret="secret123",
        installed_by="user@example.com",
        metadata={"repo_count": "5"},
    )


@pytest.mark.asyncio
async def test_create_installation(service, github_install_data):
    installation = await service.create_installation(github_install_data)

    assert installation.id is not None
    assert installation.platform == "github"
    assert installation.organization_id == "org-123"
    assert installation.access_token == "gho_test_token_123"
    assert installation.is_active is True


@pytest.mark.asyncio
async def test_get_installation_by_id(service, github_install_data):
    created = await service.create_installation(github_install_data)

    retrieved = await service.get_installation(created.id)

    assert retrieved.id == created.id
    assert retrieved.organization_id == "org-123"


@pytest.mark.asyncio
async def test_get_installation_not_found(service):
    with pytest.raises(InstallationNotFoundError):
        await service.get_installation("nonexistent-id")


@pytest.mark.asyncio
async def test_get_installation_by_org(service, github_install_data):
    await service.create_installation(github_install_data)

    installation = await service.get_installation_by_org("github", "org-123")

    assert installation.organization_id == "org-123"
    assert installation.platform == "github"


@pytest.mark.asyncio
async def test_get_installation_by_org_not_found(service):
    with pytest.raises(InstallationNotFoundError):
        await service.get_installation_by_org("github", "nonexistent-org")


@pytest.mark.asyncio
async def test_deactivate_installation(service, github_install_data):
    installation = await service.create_installation(github_install_data)

    success = await service.deactivate_installation(installation.id)

    assert success is True

    with pytest.raises(InstallationInactiveError):
        await service.get_installation(installation.id, validate_active=True)


@pytest.mark.asyncio
async def test_get_inactive_installation_without_validation(
    service, github_install_data
):
    installation = await service.create_installation(github_install_data)
    await service.deactivate_installation(installation.id)

    retrieved = await service.get_installation(installation.id, validate_active=False)

    assert retrieved.id == installation.id
    assert retrieved.is_active is False


@pytest.mark.asyncio
async def test_list_active_installations(service, github_install_data):
    install1 = await service.create_installation(github_install_data)

    jira_data = CreateInstallationInput(
        platform="jira",
        organization_id="org-456",
        organization_name="Another Org",
        access_token="jira_token",
        scopes=["read", "write"],
        webhook_secret="secret456",
        installed_by="admin@example.com",
    )
    install2 = await service.create_installation(jira_data)

    await service.deactivate_installation(install2.id)

    active = await service.list_active_installations()

    assert len(active) == 1
    assert active[0].id == install1.id


@pytest.mark.asyncio
async def test_list_active_installations_by_platform(service, github_install_data):
    await service.create_installation(github_install_data)

    jira_data = CreateInstallationInput(
        platform="jira",
        organization_id="org-456",
        organization_name="Another Org",
        access_token="jira_token",
        scopes=["read"],
        webhook_secret="secret456",
        installed_by="admin@example.com",
    )
    await service.create_installation(jira_data)

    github_only = await service.list_active_installations(platform="github")

    assert len(github_only) == 1
    assert github_only[0].platform == "github"


@pytest.mark.asyncio
async def test_get_valid_token_not_expired(service, github_install_data):
    installation = await service.create_installation(github_install_data)

    token = await service.get_valid_token(installation.id)

    assert token == "gho_test_token_123"


@pytest.mark.asyncio
async def test_get_valid_token_expired_without_refresh(service):
    expired_data = CreateInstallationInput(
        platform="github",
        organization_id="org-999",
        organization_name="Expired Org",
        access_token="expired_token",
        token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        scopes=["repo"],
        webhook_secret="secret",
        installed_by="user@example.com",
    )

    installation = await service.create_installation(expired_data)

    with pytest.raises(TokenExpiredError):
        await service.get_valid_token(installation.id)


@pytest.mark.asyncio
async def test_token_expiry_buffer():
    repository = MemoryInstallationRepository()
    service = TokenService(repository)

    almost_expired_data = CreateInstallationInput(
        platform="github",
        organization_id="org-buffer",
        organization_name="Buffer Test",
        access_token="buffer_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=3),
        scopes=["repo"],
        webhook_secret="secret",
        installed_by="user@example.com",
    )

    installation = await service.create_installation(almost_expired_data)

    assert service._is_token_expired(installation) is True
