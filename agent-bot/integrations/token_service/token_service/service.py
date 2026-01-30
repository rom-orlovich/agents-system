import structlog
from datetime import datetime, timezone, timedelta
from .models import Installation, CreateInstallationInput, Platform
from .repository import InstallationRepositoryProtocol
from .exceptions import (
    InstallationNotFoundError,
    InstallationInactiveError,
    TokenExpiredError,
)

logger = structlog.get_logger()


class TokenService:
    def __init__(self, repository: InstallationRepositoryProtocol):
        self.repository = repository

    async def create_installation(
        self, data: CreateInstallationInput
    ) -> Installation:
        logger.info(
            "creating_installation",
            platform=data.platform,
            org_id=data.organization_id,
        )

        installation = await self.repository.create(data)

        logger.info(
            "installation_created",
            installation_id=installation.id,
            platform=installation.platform,
        )

        return installation

    async def get_installation(
        self, installation_id: str, validate_active: bool = True
    ) -> Installation:
        installation = await self.repository.get_by_id(installation_id)

        if not installation:
            raise InstallationNotFoundError(
                f"Installation {installation_id} not found"
            )

        if validate_active and not installation.is_active:
            raise InstallationInactiveError(
                f"Installation {installation_id} is inactive"
            )

        return installation

    async def get_installation_by_org(
        self, platform: Platform, organization_id: str
    ) -> Installation:
        installation = await self.repository.get_by_platform_and_org(
            platform, organization_id
        )

        if not installation:
            raise InstallationNotFoundError(
                f"Installation for {platform}/{organization_id} not found"
            )

        if not installation.is_active:
            raise InstallationInactiveError(
                f"Installation for {platform}/{organization_id} is inactive"
            )

        return installation

    async def get_valid_token(self, installation_id: str) -> str:
        installation = await self.get_installation(installation_id)

        if self._is_token_expired(installation):
            if not installation.refresh_token:
                raise TokenExpiredError(
                    f"Token expired and no refresh token available"
                )

            await self._refresh_token(installation)
            installation = await self.get_installation(installation_id)

        return installation.access_token

    async def deactivate_installation(self, installation_id: str) -> bool:
        logger.info("deactivating_installation", installation_id=installation_id)

        success = await self.repository.deactivate(installation_id)

        if success:
            logger.info("installation_deactivated", installation_id=installation_id)

        return success

    async def list_active_installations(
        self, platform: Platform | None = None
    ) -> list[Installation]:
        return await self.repository.list_active(platform)

    def _is_token_expired(self, installation: Installation) -> bool:
        if not installation.token_expires_at:
            return False

        buffer_minutes = 5
        expiry_with_buffer = installation.token_expires_at - timedelta(
            minutes=buffer_minutes
        )

        return datetime.now(timezone.utc) >= expiry_with_buffer

    async def _refresh_token(self, installation: Installation) -> None:
        logger.info(
            "refreshing_token",
            installation_id=installation.id,
            platform=installation.platform,
        )

        logger.warning(
            "token_refresh_not_implemented",
            installation_id=installation.id,
            platform=installation.platform,
        )
