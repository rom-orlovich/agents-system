import pytest
from datetime import datetime, timezone
from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    InstallationFilter,
)
from token_service.repository import InMemoryInstallationRepository
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
