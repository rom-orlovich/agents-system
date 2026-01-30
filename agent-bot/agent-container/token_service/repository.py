from typing import Protocol

from .models import Installation, InstallationCreate, InstallationUpdate


class InstallationRepository(Protocol):
    async def create(self, data: InstallationCreate) -> Installation: ...

    async def get_by_id(self, installation_id: str) -> Installation | None: ...

    async def get_by_organization(
        self, platform: str, organization_id: str
    ) -> Installation | None: ...

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation | None: ...

    async def delete(self, installation_id: str) -> bool: ...

    async def list_all(self) -> list[Installation]: ...
