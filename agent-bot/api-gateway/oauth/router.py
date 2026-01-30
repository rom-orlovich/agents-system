from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse
import structlog

from .models import OAuthCallbackParams, OAuthState
from .github import GitHubOAuthHandler, GitHubOAuthError
from token_service import (
    TokenService,
    InstallationCreate,
    Platform,
)

logger = structlog.get_logger()


def create_oauth_router(
    token_service: TokenService,
    github_handler: GitHubOAuthHandler,
) -> APIRouter:
    router = APIRouter(prefix="/oauth", tags=["oauth"])

    @router.get("/github/authorize")
    async def github_authorize(redirect_uri: str) -> dict:
        import secrets

        state = OAuthState(
            platform="github",
            redirect_uri=redirect_uri,
            nonce=secrets.token_hex(16),
        )

        authorization_url = github_handler.get_authorization_url(state)

        logger.info("github_authorization_initiated", redirect_uri=redirect_uri)

        return {
            "authorization_url": authorization_url,
            "state": state.to_encoded(),
        }

    @router.get("/github/callback")
    async def github_callback(
        code: str,
        state: str,
        error: str | None = None,
        error_description: str | None = None,
    ):
        if error:
            logger.error(
                "github_oauth_error",
                error=error,
                description=error_description,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error}: {error_description}",
            )

        try:
            decoded_state = github_handler.validate_state(state)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter",
            )

        try:
            token_response = await github_handler.exchange_code(code)
        except GitHubOAuthError as e:
            logger.error("github_token_exchange_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        user_info = await github_handler.get_authenticated_user(
            token_response.access_token
        )

        webhook_secret = github_handler.generate_webhook_secret()

        installation_create = InstallationCreate(
            platform=Platform.GITHUB,
            organization_id=user_info["id"],
            organization_name=user_info["login"],
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            scopes=token_response.scopes,
            webhook_secret=webhook_secret,
            installed_by=user_info["email"] or user_info["login"],
        )

        installation = await token_service.create_installation(
            installation_create
        )

        logger.info(
            "github_installation_created",
            installation_id=installation.id,
            organization=user_info["login"],
        )

        redirect_url = f"{decoded_state.redirect_uri}?installation_id={installation.id}&webhook_secret={webhook_secret}"
        return RedirectResponse(redirect_url)

    @router.get("/health")
    async def health() -> dict:
        return {"status": "healthy"}

    return router
