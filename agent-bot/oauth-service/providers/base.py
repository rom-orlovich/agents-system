from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)


@dataclass
class InstallationInfo:
    external_org_id: str
    external_org_name: str | None = None
    external_install_id: str | None = None
    installed_by: str | None = None
    permissions: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class OAuthProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        pass

    @abstractmethod
    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        pass

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        pass

    @abstractmethod
    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        pass

    @abstractmethod
    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        pass
