from typing import Callable, Awaitable
import structlog

from .models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    TokenInfo,
)
from .repository import InstallationRepositoryPort
from .exceptions import (
    InstallationNotFoundError,
    TokenExpiredError,
)

logger = structlog.get_logger()

RefreshHandler = Callable[[Installation], Awaitable[TokenInfo]]


class TokenService:
    def __init__(
        self,
        repository: InstallationRepositoryPort,
        refresh_handlers: dict[Platform, RefreshHandler] | None = None,
    ) -> None:
        self._repository = repository
        self._refresh_handlers = refresh_handlers or {}

    async def create_installation(
        self, data: InstallationCreate
    ) -> Installation:
        logger.info(
            "creating_installation",
            platform=data.platform.value,
            organization_id=data.organization_id,
        )
        installation = await self._repository.create(data)
        logger.info(
            "installation_created",
            installation_id=installation.id,
            platform=data.platform.value,
        )
        return installation

    async def get_token(
        self,
        platform: Platform,
        organization_id: str,
    ) -> TokenInfo:
        installation = await self._get_installation(platform, organization_id)
        
        token_info = TokenInfo(
            access_token=installation.access_token,
            expires_at=installation.token_expires_at,
            scopes=installation.scopes,
        )

        if token_info.is_expired:
            logger.info(
                "token_expired_refreshing",
                installation_id=installation.id,
            )
            token_info = await self._refresh_token(installation)

        return token_info

    async def get_webhook_secret(
        self,
        platform: Platform,
        organization_id: str,
    ) -> str:
        installation = await self._get_installation(platform, organization_id)
        return installation.webhook_secret

    async def get_installation_by_id(
        self, installation_id: str
    ) -> Installation | None:
        return await self._repository.get_by_id(installation_id)

    async def deactivate_installation(
        self, installation_id: str
    ) -> Installation:
        logger.info("deactivating_installation", installation_id=installation_id)
        update = InstallationUpdate(is_active=False)
        return await self._repository.update(installation_id, update)

    async def _get_installation(
        self,
        platform: Platform,
        organization_id: str,
    ) -> Installation:
        installation = await self._repository.get_by_platform_and_org(
            platform, organization_id
        )
        if not installation:
            raise InstallationNotFoundError(platform.value, organization_id)
        if not installation.is_active:
            raise InstallationNotFoundError(platform.value, organization_id)
        return installation

    async def _refresh_token(self, installation: Installation) -> TokenInfo:
        handler = self._refresh_handlers.get(installation.platform)
        if not handler:
            raise TokenExpiredError(installation.id)

        new_token_info = await handler(installation)

        await self._repository.update(
            installation.id,
            InstallationUpdate(
                access_token=new_token_info.access_token,
                token_expires_at=new_token_info.expires_at,
            ),
        )

        logger.info(
            "token_refreshed",
            installation_id=installation.id,
        )

        return new_token_info
