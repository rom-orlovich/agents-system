import uuid
from datetime import datetime, timezone

from .models import Installation, InstallationCreate, InstallationUpdate, Platform


class InMemoryInstallationRepository:
    def __init__(self) -> None:
        self._installations: dict[str, Installation] = {}

    async def create(self, data: InstallationCreate) -> Installation:
        installation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        installation = Installation(
            id=installation_id,
            platform=data.platform,
            organization_id=data.organization_id,
            organization_name=data.organization_name,
            access_token=data.access_token,
            refresh_token=data.refresh_token,
            scopes=data.scopes,
            webhook_secret=data.webhook_secret,
            installed_by=data.installed_by,
            created_at=now,
            updated_at=now,
        )

        self._installations[installation_id] = installation
        return installation

    async def get_by_id(self, installation_id: str) -> Installation | None:
        return self._installations.get(installation_id)

    async def get_by_organization(
        self, platform: str, organization_id: str
    ) -> Installation | None:
        for installation in self._installations.values():
            if (
                installation.platform.value == platform
                and installation.organization_id == organization_id
            ):
                return installation
        return None

    async def update(
        self, installation_id: str, data: InstallationUpdate
    ) -> Installation | None:
        installation = self._installations.get(installation_id)
        if installation is None:
            return None

        update_dict = data.model_dump(exclude_none=True)
        updated_data = installation.model_dump()
        updated_data.update(update_dict)
        updated_data["updated_at"] = datetime.now(timezone.utc)

        updated_installation = Installation.model_validate(updated_data)
        self._installations[installation_id] = updated_installation

        return updated_installation

    async def delete(self, installation_id: str) -> bool:
        if installation_id in self._installations:
            del self._installations[installation_id]
            return True
        return False

    async def list_all(self) -> list[Installation]:
        return list(self._installations.values())
