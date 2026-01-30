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
