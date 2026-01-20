"""OAuth and authentication models."""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

from types.enums import TokenStatus


@dataclass
class OAuthCredentials:
    """OAuth credentials structure."""
    access_token: str
    refresh_token: str
    expires_at: int  # milliseconds
    token_type: str = "Bearer"
    scope: str = ""

    @property
    def expires_at_datetime(self) -> datetime:
        """Convert milliseconds to datetime."""
        return datetime.fromtimestamp(self.expires_at / 1000)

    @property
    def minutes_until_expiry(self) -> float:
        """Minutes until token expires."""
        now = datetime.now()
        expiry = self.expires_at_datetime
        delta = expiry - now
        return delta.total_seconds() / 60

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.minutes_until_expiry <= 0

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (<30 min left)."""
        return self.minutes_until_expiry < 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "expiresAt": self.expires_at,
            "tokenType": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthCredentials":
        """Create from dictionary."""
        return cls(
            access_token=data.get("accessToken", ""),
            refresh_token=data.get("refreshToken", ""),
            expires_at=data.get("expiresAt", 0),
            token_type=data.get("tokenType", "Bearer"),
            scope=data.get("scope", ""),
        )


@dataclass
class TokenRefreshResult:
    """Result of a token refresh operation."""
    success: bool
    credentials: Optional[OAuthCredentials] = None
    error: Optional[str] = None
    status: TokenStatus = TokenStatus.UNKNOWN
