from token_service.models import Installation
from token_service.exceptions import InstallationNotFoundError


class InstallationRepository:
    def __init__(self) -> None:
        self._installations: dict[str, Installation] = {}

    async def save(self, installation: Installation) -> None:
        self._installations[installation.id] = installation

    async def get_by_id(self, installation_id: str) -> Installation:
        if installation_id not in self._installations:
            raise InstallationNotFoundError(
                f"Installation {installation_id} not found"
            )
        return self._installations[installation_id]

    async def get_by_organization(
        self, organization_id: str, platform: str
    ) -> Installation:
        for installation in self._installations.values():
            if (
                installation.organization_id == organization_id
                and installation.platform == platform
                and installation.is_active
            ):
                return installation
        raise InstallationNotFoundError(
            f"No active installation for org {organization_id} on {platform}"
        )

    async def list_by_organization(
        self, organization_id: str
    ) -> list[Installation]:
        return [
            inst
            for inst in self._installations.values()
            if inst.organization_id == organization_id and inst.is_active
        ]

    async def deactivate(self, installation_id: str) -> None:
        installation = await self.get_by_id(installation_id)
        installation.is_active = False
        await self.save(installation)
