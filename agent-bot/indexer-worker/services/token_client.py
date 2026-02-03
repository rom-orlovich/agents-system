import httpx
import structlog
from typing import Protocol, runtime_checkable

from config import settings


logger = structlog.get_logger()


@runtime_checkable
class TokenProviderProtocol(Protocol):
    async def get_token(self, platform: str, org_id: str) -> str | None: ...
    async def is_connected(self, platform: str) -> bool: ...


class OAuthTokenClient:
    """Token client that fetches tokens from the OAuth service."""

    def __init__(self, oauth_service_url: str, timeout: float = 10.0):
        self._oauth_url = oauth_service_url.rstrip("/")
        self._timeout = timeout
        self._token_cache: dict[tuple[str, str], tuple[str, float]] = {}

    async def get_token(self, platform: str, org_id: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._oauth_url}/oauth/token/{platform}",
                    params={"org_id": org_id},
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("available"):
                        token = data.get("token")
                        logger.debug(
                            "oauth_token_retrieved",
                            platform=platform,
                            org_id=org_id,
                        )
                        return token
                    else:
                        logger.warning(
                            "oauth_token_not_available",
                            platform=platform,
                            org_id=org_id,
                        )
                else:
                    logger.warning(
                        "oauth_token_request_failed",
                        platform=platform,
                        org_id=org_id,
                        status=response.status_code,
                    )
        except httpx.RequestError as e:
            logger.error(
                "oauth_service_unreachable",
                platform=platform,
                org_id=org_id,
                error=str(e),
            )
        return None

    async def is_connected(self, platform: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._oauth_url}/oauth/installations",
                    params={"platform": platform},
                )
                if response.status_code == 200:
                    data = response.json()
                    installations = data.get("installations", [])
                    return len(installations) > 0
        except httpx.RequestError as e:
            logger.warning(
                "oauth_connection_check_failed",
                platform=platform,
                error=str(e),
            )
        return False


class StaticTokenProvider:
    """Fallback token provider using static environment variables."""

    def __init__(
        self,
        github_token: str = "",
        jira_token: str = "",
        confluence_token: str = "",
    ):
        self._tokens = {
            "github": github_token,
            "jira": jira_token,
            "confluence": confluence_token,
        }

    async def get_token(self, platform: str, org_id: str) -> str | None:
        token = self._tokens.get(platform)
        if token:
            logger.debug(
                "static_token_used",
                platform=platform,
                org_id=org_id,
            )
        return token if token else None

    async def is_connected(self, platform: str) -> bool:
        return bool(self._tokens.get(platform))


class HybridTokenProvider:
    """Token provider that tries OAuth first, then falls back to static tokens."""

    def __init__(
        self,
        oauth_client: OAuthTokenClient | None,
        static_provider: StaticTokenProvider,
        use_oauth: bool = True,
    ):
        self._oauth_client = oauth_client
        self._static_provider = static_provider
        self._use_oauth = use_oauth

    async def get_token(self, platform: str, org_id: str) -> str | None:
        if self._use_oauth and self._oauth_client:
            token = await self._oauth_client.get_token(platform, org_id)
            if token:
                return token
            logger.debug(
                "oauth_token_unavailable_using_static",
                platform=platform,
                org_id=org_id,
            )

        return await self._static_provider.get_token(platform, org_id)

    async def is_connected(self, platform: str) -> bool:
        if self._use_oauth and self._oauth_client:
            if await self._oauth_client.is_connected(platform):
                return True

        return await self._static_provider.is_connected(platform)


def create_token_provider() -> HybridTokenProvider:
    """Factory function to create the appropriate token provider."""
    oauth_client = None
    if settings.use_oauth:
        oauth_client = OAuthTokenClient(settings.oauth_service_url)

    static_provider = StaticTokenProvider(
        github_token=settings.github_token,
        jira_token=settings.jira_api_token,
        confluence_token=settings.confluence_api_token,
    )

    return HybridTokenProvider(
        oauth_client=oauth_client,
        static_provider=static_provider,
        use_oauth=settings.use_oauth,
    )
