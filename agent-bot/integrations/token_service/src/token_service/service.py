from datetime import datetime, timezone, timedelta
from token_service.models import Installation
from token_service.repository import InstallationRepository
from token_service.exceptions import TokenExpiredError, TokenRefreshError
import structlog

logger = structlog.get_logger()


class TokenService:
    def __init__(self, repository: InstallationRepository | None = None) -> None:
        self.repository = repository or InstallationRepository()

    async def create_installation(self, installation: Installation) -> None:
        logger.info(
            "creating_installation",
            installation_id=installation.id,
            organization=installation.organization_name,
            platform=installation.platform,
        )
        await self.repository.save(installation)

    async def get_installation(self, installation_id: str) -> Installation:
        return await self.repository.get_by_id(installation_id)

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

    async def deactivate_installation(self, installation_id: str) -> None:
        logger.info("deactivating_installation", installation_id=installation_id)
        await self.repository.deactivate(installation_id)

    async def list_organization_installations(
        self, organization_id: str
    ) -> list[Installation]:
        return await self.repository.list_by_organization(organization_id)

    def _is_token_expired(self, installation: Installation) -> bool:
        if not installation.token_expires_at:
            return False

        buffer = timedelta(minutes=5)
        expiry_with_buffer = installation.token_expires_at - buffer
        return datetime.now(timezone.utc) > expiry_with_buffer

    async def _refresh_token(self, installation: Installation) -> None:
        logger.info("refreshing_token", installation_id=installation.id)
        raise TokenRefreshError("Token refresh not implemented")
