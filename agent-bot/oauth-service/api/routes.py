from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings
from providers.github import GitHubOAuthProvider
from providers.jira import JiraOAuthProvider
from providers.slack import SlackOAuthProvider
from services.installation_service import InstallationService
from services.token_service import TokenService

from .server import get_session

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])

PROVIDERS = {
    "github": GitHubOAuthProvider,
    "slack": SlackOAuthProvider,
    "jira": JiraOAuthProvider,
}


@router.get("/install/{platform}")
async def start_installation(
    platform: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if platform not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    provider = PROVIDERS[platform](settings)
    installation_service = InstallationService(session)

    code_verifier = None
    if platform == "jira":
        code_verifier = provider._generate_code_verifier()

    state = await installation_service.create_oauth_state(
        platform=platform,
        code_verifier=code_verifier,
    )

    if platform == "jira" and code_verifier:
        provider._code_verifiers[state] = code_verifier

    auth_url = provider.get_authorization_url(state)
    logger.info("oauth_flow_started", platform=platform, state=state[:8])

    return RedirectResponse(url=auth_url)


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(...),
    installation_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if platform not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    installation_service = InstallationService(session)
    oauth_state = await installation_service.validate_oauth_state(state)

    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    provider = PROVIDERS[platform](settings)

    if platform == "jira" and oauth_state.code_verifier:
        provider._code_verifiers[state] = oauth_state.code_verifier

    if platform == "github" and installation_id:
        info = await provider.get_installation_by_id(installation_id)
        tokens = await provider.get_installation_token(installation_id)
    else:
        tokens = await provider.exchange_code(code, state)
        info = await provider.get_installation_info(tokens)

    installation = await installation_service.create_installation(
        platform=platform,
        tokens=tokens,
        info=info,
    )

    logger.info(
        "oauth_installation_created",
        platform=platform,
        org_id=info.external_org_id,
        installation_id=str(installation.id),
    )

    return {
        "success": True,
        "installation_id": str(installation.id),
        "org_name": info.external_org_name,
    }


@router.get("/installations")
async def list_installations(
    platform: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    installation_service = InstallationService(session)
    installations = await installation_service.list_installations(platform)
    return {"installations": installations}


@router.delete("/installations/{installation_id}")
async def revoke_installation(
    installation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    installation_service = InstallationService(session)
    success = await installation_service.revoke_installation(installation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Installation not found")

    return {"success": True}


@router.get("/token/{platform}")
async def get_token(
    platform: str,
    org_id: str | None = Query(None),
    install_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if platform not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    token_service = TokenService(session)

    if platform == "github" and install_id:
        token = await token_service.get_github_installation_token(install_id)
    else:
        token = await token_service.get_token(platform, org_id=org_id)

    if not token:
        raise HTTPException(status_code=404, detail="No active installation found")

    return {"token": token[:10] + "..." if token else None, "available": bool(token)}
