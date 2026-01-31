from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Platform(str, Enum):
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    SENTRY = "sentry"


class InstallationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class Installation(Base):
    __tablename__ = "installations"
    __table_args__ = (
        Index("ix_installations_platform_org", "platform", "external_org_id"),
        Index("ix_installations_platform_status", "platform", "status"),
    )

    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InstallationStatus.ACTIVE.value
    )

    external_org_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_org_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_install_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    private_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    installed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, name="metadata"
    )

    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    code_verifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, name="metadata"
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
