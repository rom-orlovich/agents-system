import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.models import Installation, InstallationStatus, OAuthState
from providers.base import InstallationInfo, OAuthTokens

logger = structlog.get_logger(__name__)


class InstallationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_oauth_state(
        self,
        platform: str,
        code_verifier: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        oauth_state = OAuthState(
            state=state,
            platform=platform,
            code_verifier=code_verifier,
            metadata_json=metadata or {},
            expires_at=expires_at,
        )
        self.session.add(oauth_state)
        await self.session.commit()

        logger.info("oauth_state_created", platform=platform, state=state[:8])
        return state

    async def validate_oauth_state(self, state: str) -> OAuthState | None:
        query = select(OAuthState).where(
            OAuthState.state == state,
            OAuthState.expires_at > datetime.now(timezone.utc),
        )
        result = await self.session.execute(query)
        oauth_state = result.scalar_one_or_none()

        if oauth_state:
            await self.session.delete(oauth_state)
            await self.session.commit()

        return oauth_state

    async def create_installation(
        self,
        platform: str,
        tokens: OAuthTokens,
        info: InstallationInfo,
    ) -> Installation:
        existing = await self.get_installation_by_org(platform, info.external_org_id)
        if existing:
            existing.access_token = tokens.access_token
            existing.refresh_token = tokens.refresh_token
            existing.token_expires_at = tokens.expires_at
            existing.scopes = tokens.scopes
            existing.status = InstallationStatus.ACTIVE.value
            existing.external_org_name = info.external_org_name
            existing.external_install_id = info.external_install_id
            existing.permissions = info.permissions
            existing.metadata_json = info.metadata
            await self.session.commit()
            logger.info(
                "installation_updated", platform=platform, org_id=info.external_org_id
            )
            return existing

        installation = Installation(
            platform=platform,
            status=InstallationStatus.ACTIVE.value,
            external_org_id=info.external_org_id,
            external_org_name=info.external_org_name,
            external_install_id=info.external_install_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_expires_at=tokens.expires_at,
            scopes=tokens.scopes,
            permissions=info.permissions,
            installed_by=info.installed_by,
            metadata_json=info.metadata,
        )
        self.session.add(installation)
        await self.session.commit()

        logger.info(
            "installation_created", platform=platform, org_id=info.external_org_id
        )
        return installation

    async def get_installation_by_org(
        self, platform: str, org_id: str
    ) -> Installation | None:
        query = select(Installation).where(
            Installation.platform == platform,
            Installation.external_org_id == org_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_installation_by_id(
        self, installation_id: UUID
    ) -> Installation | None:
        query = select(Installation).where(Installation.id == installation_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_installations(
        self, platform: str | None = None
    ) -> list[dict[str, Any]]:
        query = select(Installation).where(
            Installation.status == InstallationStatus.ACTIVE.value
        )
        if platform:
            query = query.where(Installation.platform == platform)

        result = await self.session.execute(query)
        installations = result.scalars().all()

        return [
            {
                "id": str(inst.id),
                "platform": inst.platform,
                "org_id": inst.external_org_id,
                "org_name": inst.external_org_name,
                "install_id": inst.external_install_id,
                "scopes": inst.scopes,
                "created_at": inst.created_at.isoformat(),
                "last_used_at": inst.last_used_at.isoformat()
                if inst.last_used_at
                else None,
            }
            for inst in installations
        ]

    async def revoke_installation(self, installation_id: UUID) -> bool:
        installation = await self.get_installation_by_id(installation_id)
        if not installation:
            return False

        installation.status = InstallationStatus.REVOKED.value
        installation.revoked_at = datetime.now(timezone.utc)
        installation.access_token = None
        installation.refresh_token = None
        await self.session.commit()

        logger.info(
            "installation_revoked",
            platform=installation.platform,
            org_id=installation.external_org_id,
        )
        return True
