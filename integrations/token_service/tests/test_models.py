import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from token_service.models import (
    Platform,
    Installation,
    InstallationCreate,
    InstallationUpdate,
    TokenInfo,
)


class TestPlatformEnum:
    def test_valid_platforms(self):
        assert Platform.GITHUB == "github"
        assert Platform.SLACK == "slack"
        assert Platform.JIRA == "jira"
        assert Platform.SENTRY == "sentry"

    def test_platform_from_string(self):
        assert Platform("github") == Platform.GITHUB


class TestInstallation:
    def test_create_valid_installation(self):
        now = datetime.now(timezone.utc)
        installation = Installation(
            id="inst-123",
            platform=Platform.GITHUB,
            organization_id="org-456",
            organization_name="My Org",
            access_token="gho_xxxx",
            refresh_token="ghr_xxxx",
            token_expires_at=now,
            scopes=["repo", "read:org"],
            webhook_secret="whsec_xxxx",
            installed_at=now,
            installed_by="user@example.com",
            is_active=True,
        )
        assert installation.id == "inst-123"
        assert installation.platform == Platform.GITHUB

    def test_reject_invalid_platform(self):
        with pytest.raises(ValidationError) as exc_info:
            Installation(
                id="inst-123",
                platform="invalid",
                organization_id="org-456",
                organization_name="My Org",
                access_token="token",
                webhook_secret="secret",
                installed_at=datetime.now(timezone.utc),
                installed_by="user@example.com",
                scopes=[],
                is_active=True,
            )
        assert "platform" in str(exc_info.value)

    def test_strict_mode_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            Installation(
                id="inst-123",
                platform="github",
                organization_id="org-456",
                organization_name="My Org",
                access_token="token",
                webhook_secret="secret",
                installed_at=datetime.now(timezone.utc),
                installed_by="user@example.com",
                scopes=[],
                is_active=True,
                extra_field="not_allowed",
            )


class TestInstallationCreate:
    def test_create_input_valid(self):
        create_input = InstallationCreate(
            platform=Platform.GITHUB,
            organization_id="org-456",
            organization_name="My Org",
            access_token="gho_xxxx",
            refresh_token="ghr_xxxx",
            token_expires_at=datetime.now(timezone.utc),
            scopes=["repo"],
            webhook_secret="whsec_xxxx",
            installed_by="user@example.com",
        )
        assert create_input.platform == Platform.GITHUB


class TestTokenInfo:
    def test_token_is_expired(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        token_info = TokenInfo(
            access_token="token",
            expires_at=past,
            scopes=["repo"],
        )
        assert token_info.is_expired is True

    def test_token_is_not_expired(self):
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        token_info = TokenInfo(
            access_token="token",
            expires_at=future,
            scopes=["repo"],
        )
        assert token_info.is_expired is False

    def test_token_without_expiry_is_not_expired(self):
        token_info = TokenInfo(
            access_token="token",
            expires_at=None,
            scopes=["repo"],
        )
        assert token_info.is_expired is False
