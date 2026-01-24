"""OAuth usage tracking for Claude Code CLI."""

import json
from typing import Optional
from pathlib import Path

import httpx
from pydantic import BaseModel

from core.config import settings
from shared.machine_models import ClaudeCredentials
import structlog

logger = structlog.get_logger()


class SessionUsage(BaseModel):
    """Session (5-hour) usage data."""
    used: int
    limit: int
    
    @property
    def remaining(self) -> int:
        """Remaining usage in current session."""
        return max(0, self.limit - self.used)
    
    @property
    def percentage(self) -> float:
        """Usage percentage."""
        if self.limit == 0:
            return 0.0
        return min(100.0, (self.used / self.limit) * 100.0)
    
    @property
    def is_exceeded(self) -> bool:
        """Check if limit is exceeded."""
        return self.used >= self.limit


class WeeklyUsage(BaseModel):
    """Weekly (7-day) usage data."""
    used: int
    limit: int
    
    @property
    def remaining(self) -> int:
        """Remaining usage in current week."""
        return max(0, self.limit - self.used)
    
    @property
    def percentage(self) -> float:
        """Usage percentage."""
        if self.limit == 0:
            return 0.0
        return min(100.0, (self.used / self.limit) * 100.0)
    
    @property
    def is_exceeded(self) -> bool:
        """Check if limit is exceeded."""
        return self.used >= self.limit


class OAuthUsageResponse(BaseModel):
    """OAuth usage API response."""
    session: Optional[SessionUsage] = None
    weekly: Optional[WeeklyUsage] = None
    error: Optional[str] = None
    
    @property
    def is_available(self) -> bool:
        """Check if usage data is available."""
        return self.session is not None or self.weekly is not None


def load_credentials() -> Optional[ClaudeCredentials]:
    """Load credentials from file.
    
    Handles both formats:
    1. Direct format: {"access_token": "...", "refresh_token": "...", ...}
    2. Wrapped format: {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...", ...}}
    """
    creds_path = settings.credentials_path
    if not creds_path.exists():
        logger.debug("credentials_file_not_found", path=str(creds_path))
        return None
    
    try:
        creds_data = json.loads(creds_path.read_text())
        creds = ClaudeCredentials.from_dict(creds_data)
        return creds
    except Exception as e:
        logger.error("failed_to_load_credentials", error=str(e))
        return None


async def fetch_oauth_usage() -> OAuthUsageResponse:
    """
    Fetch OAuth usage data from Anthropic API.
    
    Returns:
        OAuthUsageResponse with session and weekly usage data, or error message.
    """
    creds = load_credentials()
    if not creds:
        return OAuthUsageResponse(
            error="No credentials found. Please upload credentials via /api/credentials/upload"
        )
    
    if creds.is_expired:
        return OAuthUsageResponse(
            error=f"Credentials expired at {creds.expires_at_datetime.isoformat()}"
        )
    
    url = "https://api.anthropic.com/api/oauth/usage"
    
    # Try multiple authentication methods
    auth_variants = [
        # Method 1: Authorization header only
        {
            "Authorization": f"{creds.token_type} {creds.access_token}",
            "Content-Type": "application/json",
        },
        # Method 2: Authorization + x-api-key
        {
            "Authorization": f"{creds.token_type} {creds.access_token}",
            "x-api-key": creds.access_token,
            "Content-Type": "application/json",
        },
        # Method 3: x-api-key only
        {
            "x-api-key": creds.access_token,
            "Content-Type": "application/json",
        },
    ]
    
    for i, headers in enumerate(auth_variants, 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Parse response - handle different possible formats
                        session_data = None
                        weekly_data = None
                        
                        if isinstance(data, dict):
                            # Check for nested usage object
                            if "usage" in data:
                                usage = data["usage"]
                                if "session" in usage:
                                    session_data = usage["session"]
                                if "weekly" in usage:
                                    weekly_data = usage["weekly"]
                            else:
                                # Check for direct session/weekly fields
                                if "session" in data:
                                    session_data = data["session"]
                                if "weekly" in data:
                                    weekly_data = data["weekly"]
                            
                            # Also check for direct fields (override if found)
                            if "session_used" in data or "session_limit" in data:
                                session_data = {
                                    "used": data.get("session_used", 0),
                                    "limit": data.get("session_limit", 0),
                                }
                            if "weekly_used" in data or "weekly_limit" in data:
                                weekly_data = {
                                    "used": data.get("weekly_used", 0),
                                    "limit": data.get("weekly_limit", 0),
                                }
                        
                        # Build response
                        result = OAuthUsageResponse()
                        
                        if session_data:
                            try:
                                result.session = SessionUsage(**session_data)
                            except Exception as e:
                                logger.warning("failed_to_parse_session_usage", error=str(e), data=session_data)
                        
                        if weekly_data:
                            try:
                                result.weekly = WeeklyUsage(**weekly_data)
                            except Exception as e:
                                logger.warning("failed_to_parse_weekly_usage", error=str(e), data=weekly_data)
                        
                        if result.is_available:
                            logger.info("oauth_usage_fetched", method=i, has_session=result.session is not None, has_weekly=result.weekly is not None)
                            return result
                        else:
                            logger.warning("oauth_usage_empty_response", method=i, response_data=data)
                            # Try next method
                            continue
                    
                    except json.JSONDecodeError as e:
                        logger.warning("invalid_json_response", method=i, error=str(e), text=response.text[:200])
                        continue
                
                elif response.status_code == 401:
                    logger.debug("auth_failed_method", method=i, status=401)
                    # Try next authentication method
                    continue
                
                elif response.status_code == 404:
                    return OAuthUsageResponse(
                        error="Usage endpoint not found (404). Endpoint may have changed."
                    )
                
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    except Exception:
                        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    
                    logger.warning("oauth_usage_request_failed", method=i, status=response.status_code, error=error_msg)
                    # Try next method
                    continue
        
        except httpx.TimeoutException:
            logger.warning("oauth_usage_timeout", method=i)
            continue
        except httpx.ConnectError as e:
            return OAuthUsageResponse(
                error=f"Connection error: {str(e)}"
            )
        except Exception as e:
            logger.warning("oauth_usage_error", method=i, error=str(e), error_type=type(e).__name__)
            continue
    
    # All methods failed
    return OAuthUsageResponse(
        error="Failed to fetch usage data. All authentication methods failed. Credentials may be invalid or expired."
    )
