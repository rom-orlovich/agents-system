from typing import Protocol
from .models import Installation, CreateInstallationInput, Platform


class InstallationRepositoryProtocol(Protocol):
    async def create(self, data: CreateInstallationInput) -> Installation: ...

    async def get_by_id(self, installation_id: str) -> Installation | None: ...

    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None: ...

    async def update_token(
        self,
        installation_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
    ) -> bool: ...

    async def deactivate(self, installation_id: str) -> bool: ...

    async def list_active(self, platform: Platform | None = None) -> list[Installation]: ...


class MemoryInstallationRepository:
    def __init__(self):
        self._installations: dict[str, Installation] = {}

    async def create(self, data: CreateInstallationInput) -> Installation:
        import uuid
        from datetime import datetime, timezone

        installation_id = str(uuid.uuid4())
        installation = Installation(
            id=installation_id,
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
        self._installations[installation_id] = installation
        return installation

    async def get_by_id(self, installation_id: str) -> Installation | None:
        return self._installations.get(installation_id)

    async def get_by_platform_and_org(
        self, platform: Platform, organization_id: str
    ) -> Installation | None:
        for inst in self._installations.values():
            if inst.platform == platform and inst.organization_id == organization_id:
                return inst
        return None

    async def update_token(
        self,
        installation_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
    ) -> bool:
        from datetime import datetime

        installation = self._installations.get(installation_id)
        if not installation:
            return False

        installation.access_token = access_token
        installation.refresh_token = refresh_token
        if expires_at:
            installation.token_expires_at = datetime.fromisoformat(expires_at)

        self._installations[installation_id] = installation
        return True

    async def deactivate(self, installation_id: str) -> bool:
        installation = self._installations.get(installation_id)
        if not installation:
            return False

        installation.is_active = False
        self._installations[installation_id] = installation
        return True

    async def list_active(self, platform: Platform | None = None) -> list[Installation]:
        result = [inst for inst in self._installations.values() if inst.is_active]
        if platform:
            result = [inst for inst in result if inst.platform == platform]
        return result
