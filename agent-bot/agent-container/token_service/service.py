import structlog

from .models import Installation, InstallationCreate, InstallationUpdate
from .repository import InstallationRepository

logger = structlog.get_logger()


class TokenServiceError(Exception):
    pass


class InstallationNotFoundError(TokenServiceError):
    pass


class TokenService:
    def __init__(self, repository: InstallationRepository) -> None:
        self._repository = repository

    async def create_installation(
        self, data: InstallationCreate
    ) -> Installation:
        logger.info(
            "creating_installation",
            platform=data.platform.value,
            organization=data.organization_name,
        )

        installation = await self._repository.create(data)

        logger.info(
            "installation_created",
            installation_id=installation.id,
            platform=installation.platform.value,
        )

        return installation

    async def get_installation(
        self, installation_id: str
    ) -> Installation:
        installation = await self._repository.get_by_id(installation_id)

        if installation is None:
            raise InstallationNotFoundError(
                f"Installation {installation_id} not found"
            )

        return installation

    async def get_installation_by_organization(
        self, platform: str, organization_id: str
    ) -> Installation:
        installation = await self._repository.get_by_organization(
            platform, organization_id
        )

        if installation is None:
            raise InstallationNotFoundError(
                f"Installation for {platform}/{organization_id} not found"
            )

        return installation

    async def update_installation(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation:
        installation = await self._repository.update(installation_id, data)

        if installation is None:
            raise InstallationNotFoundError(
                f"Installation {installation_id} not found"
            )

        logger.info(
            "installation_updated",
            installation_id=installation_id,
        )

        return installation

    async def delete_installation(self, installation_id: str) -> None:
        deleted = await self._repository.delete(installation_id)

        if not deleted:
            raise InstallationNotFoundError(
                f"Installation {installation_id} not found"
            )

        logger.info("installation_deleted", installation_id=installation_id)

    async def list_installations(self) -> list[Installation]:
        return await self._repository.list_all()
