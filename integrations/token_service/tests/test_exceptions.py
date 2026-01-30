import pytest
from token_service.exceptions import (
    TokenServiceError,
    InstallationNotFoundError,
    TokenExpiredError,
    TokenRefreshError,
)


class TestExceptions:
    def test_installation_not_found_error(self):
        error = InstallationNotFoundError(
            platform="github",
            organization_id="org-123",
        )
        assert "github" in str(error)
        assert "org-123" in str(error)

    def test_token_expired_error(self):
        error = TokenExpiredError(installation_id="inst-123")
        assert "inst-123" in str(error)

    def test_token_refresh_error(self):
        error = TokenRefreshError(
            installation_id="inst-123",
            reason="invalid_grant",
        )
        assert "inst-123" in str(error)
        assert "invalid_grant" in str(error)

    def test_inheritance(self):
        assert issubclass(InstallationNotFoundError, TokenServiceError)
        assert issubclass(TokenExpiredError, TokenServiceError)
        assert issubclass(TokenRefreshError, TokenServiceError)
