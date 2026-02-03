"""OAuth status and integration management API."""

import os
from typing import Literal

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger()
router = APIRouter()

OAUTH_SERVICE_URL = os.getenv("OAUTH_SERVICE_URL", "http://oauth-service:8010")

SUPPORTED_PLATFORMS = ["github", "jira", "slack", "sentry"]

PLATFORM_CONFIG = {
    "github": {
        "name": "GitHub",
        "icon": "github",
        "description": "Connect to GitHub for repository access",
        "required_env": ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"],
    },
    "jira": {
        "name": "Jira",
        "icon": "clipboard-list",
        "description": "Connect to Jira for issue tracking",
        "required_env": ["JIRA_CLIENT_ID", "JIRA_CLIENT_SECRET"],
    },
    "slack": {
        "name": "Slack",
        "icon": "message-square",
        "description": "Connect to Slack for notifications",
        "required_env": ["SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET"],
    },
    "sentry": {
        "name": "Sentry",
        "icon": "alert-triangle",
        "description": "Connect to Sentry for error tracking",
        "required_env": ["SENTRY_AUTH_TOKEN"],
    },
}


class OAuthStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    platform: str
    name: str
    connected: bool
    configured: bool
    icon: str
    description: str
    installed_at: str | None = None
    scopes: list[str] | None = None


class OAuthStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    statuses: dict[str, OAuthStatus]


class OAuthInstallResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    redirect_url: str


class OAuthRevokeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    platform: str
    message: str


def is_platform_configured(platform: str) -> bool:
    config = PLATFORM_CONFIG.get(platform, {})
    required_env = config.get("required_env", [])
    return all(os.getenv(var) for var in required_env)


@router.get("/oauth/status")
async def get_all_oauth_status() -> OAuthStatusResponse:
    """Get OAuth connection status for all platforms."""
    statuses: dict[str, OAuthStatus] = {}

    for platform in SUPPORTED_PLATFORMS:
        config = PLATFORM_CONFIG.get(platform, {})
        configured = is_platform_configured(platform)
        connected = False
        installed_at = None
        scopes = None

        if configured:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{OAUTH_SERVICE_URL}/oauth/installations",
                        params={"platform": platform},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        installations = data.get("installations", [])
                        if installations:
                            connected = True
                            latest = installations[0]
                            installed_at = latest.get("installed_at")
                            scopes = latest.get("scopes")
            except httpx.RequestError as e:
                logger.warning(
                    "oauth_service_unreachable",
                    platform=platform,
                    error=str(e),
                )

        statuses[platform] = OAuthStatus(
            platform=platform,
            name=config.get("name", platform.title()),
            connected=connected,
            configured=configured,
            icon=config.get("icon", "link"),
            description=config.get("description", ""),
            installed_at=installed_at,
            scopes=scopes,
        )

    return OAuthStatusResponse(success=True, statuses=statuses)


@router.get("/oauth/status/{platform}")
async def get_platform_oauth_status(
    platform: Literal["github", "jira", "slack", "sentry"],
) -> OAuthStatus:
    """Get OAuth connection status for a specific platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    config = PLATFORM_CONFIG.get(platform, {})
    configured = is_platform_configured(platform)
    connected = False
    installed_at = None
    scopes = None

    if configured:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{OAUTH_SERVICE_URL}/oauth/installations",
                    params={"platform": platform},
                )
                if response.status_code == 200:
                    data = response.json()
                    installations = data.get("installations", [])
                    if installations:
                        connected = True
                        latest = installations[0]
                        installed_at = latest.get("installed_at")
                        scopes = latest.get("scopes")
        except httpx.RequestError as e:
            logger.warning(
                "oauth_service_unreachable",
                platform=platform,
                error=str(e),
            )

    return OAuthStatus(
        platform=platform,
        name=config.get("name", platform.title()),
        connected=connected,
        configured=configured,
        icon=config.get("icon", "link"),
        description=config.get("description", ""),
        installed_at=installed_at,
        scopes=scopes,
    )


@router.post("/oauth/install/{platform}")
async def start_oauth_install(
    platform: Literal["github", "jira", "slack", "sentry"],
) -> OAuthInstallResponse:
    """Start OAuth installation flow for a platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if not is_platform_configured(platform):
        raise HTTPException(
            status_code=400,
            detail=f"Platform {platform} is not configured. Check environment variables.",
        )

    redirect_url = f"{OAUTH_SERVICE_URL}/oauth/install/{platform}"

    return OAuthInstallResponse(success=True, redirect_url=redirect_url)


@router.delete("/oauth/revoke/{platform}")
async def revoke_oauth(
    platform: Literal["github", "jira", "slack", "sentry"],
) -> OAuthRevokeResponse:
    """Revoke OAuth connection for a platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{OAUTH_SERVICE_URL}/oauth/installations",
                params={"platform": platform},
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Failed to fetch installations"
                )

            data = response.json()
            installations = data.get("installations", [])

            if not installations:
                return OAuthRevokeResponse(
                    success=True,
                    platform=platform,
                    message="No installation found to revoke",
                )

            for installation in installations:
                installation_id = installation.get("installation_id")
                if installation_id:
                    delete_response = await client.delete(
                        f"{OAUTH_SERVICE_URL}/oauth/installations/{installation_id}"
                    )
                    if delete_response.status_code != 200:
                        logger.warning(
                            "oauth_revoke_failed",
                            platform=platform,
                            installation_id=installation_id,
                        )

            return OAuthRevokeResponse(
                success=True,
                platform=platform,
                message=f"Successfully revoked {len(installations)} installation(s)",
            )

    except httpx.RequestError as e:
        logger.error("oauth_revoke_error", platform=platform, error=str(e))
        raise HTTPException(
            status_code=503, detail=f"OAuth service unavailable: {str(e)}"
        )
