from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.models import Installation, InstallationStatus, Platform
from config.settings import get_settings
from providers.github import GitHubOAuthProvider
from providers.jira import JiraOAuthProvider
from providers.slack import SlackOAuthProvider

logger = structlog.get_logger(__name__)


class TokenService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_token(
        self,
        platform: str,
        org_id: str | None = None,
        installation_id: UUID | None = None,
    ) -> str | None:
        query = select(Installation).where(
            Installation.platform == platform,
            Installation.status == InstallationStatus.ACTIVE.value,
        )

        if installation_id:
            query = query.where(Installation.id == installation_id)
        elif org_id:
            query = query.where(Installation.external_org_id == org_id)
        else:
            return None

        result = await self.session.execute(query)
        installation = result.scalar_one_or_none()

        if not installation:
            return None

        if self._is_token_expired(installation):
            new_token = await self._refresh_token(installation)
            if new_token:
                return new_token
            return None

        await self._update_last_used(installation)
        return installation.access_token

    async def get_github_installation_token(
        self, external_install_id: str
    ) -> str | None:
        query = select(Installation).where(
            Installation.platform == Platform.GITHUB.value,
            Installation.external_install_id == external_install_id,
            Installation.status == InstallationStatus.ACTIVE.value,
        )
        result = await self.session.execute(query)
        installation = result.scalar_one_or_none()

        if not installation:
            return None

        if not self._is_github_token_expired(installation):
            await self._update_last_used(installation)
            return installation.access_token

        settings = get_settings()
        provider = GitHubOAuthProvider(settings)
        tokens = await provider.get_installation_token(external_install_id)

        installation.access_token = tokens.access_token
        installation.token_expires_at = tokens.expires_at
        await self.session.commit()

        logger.info(
            "github_token_refreshed",
            install_id=external_install_id,
        )
        return tokens.access_token

    async def get_all_installations(self, platform: str) -> list[Installation]:
        query = select(Installation).where(
            Installation.platform == platform,
            Installation.status == InstallationStatus.ACTIVE.value,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def _is_token_expired(self, installation: Installation) -> bool:
        if not installation.token_expires_at:
            return False
        return installation.token_expires_at < datetime.now(timezone.utc)

    def _is_github_token_expired(self, installation: Installation) -> bool:
        if not installation.token_expires_at:
            return True
        buffer = timedelta(minutes=5)
        return installation.token_expires_at < datetime.now(timezone.utc) + buffer

    async def _refresh_token(self, installation: Installation) -> str | None:
        if not installation.refresh_token:
            return None

        settings = get_settings()
        providers = {
            Platform.SLACK.value: SlackOAuthProvider,
            Platform.JIRA.value: JiraOAuthProvider,
        }

        provider_class = providers.get(installation.platform)
        if not provider_class:
            return None

        provider = provider_class(settings)
        tokens = await provider.refresh_tokens(installation.refresh_token)

        installation.access_token = tokens.access_token
        installation.refresh_token = tokens.refresh_token or installation.refresh_token
        installation.token_expires_at = tokens.expires_at
        await self.session.commit()

        logger.info(
            "token_refreshed",
            platform=installation.platform,
            org_id=installation.external_org_id,
        )
        return tokens.access_token

    async def _update_last_used(self, installation: Installation) -> None:
        installation.last_used_at = datetime.now(timezone.utc)
        await self.session.commit()
