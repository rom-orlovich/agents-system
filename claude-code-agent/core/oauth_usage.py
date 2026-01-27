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
    """Session (5-hour) usage data from Anthropic OAuth API."""
    utilization: float  # Percentage used (0-100)
    resets_at: Optional[str] = None  # ISO timestamp when limit resets

    @property
    def percentage(self) -> float:
        """Usage percentage (already provided by API)."""
        return min(100.0, max(0.0, self.utilization))

    @property
    def remaining_percentage(self) -> float:
        """Remaining percentage."""
        return max(0.0, 100.0 - self.utilization)

    @property
    def is_exceeded(self) -> bool:
        """Check if limit is exceeded (>= 100%)."""
        return self.utilization >= 100.0


class WeeklyUsage(BaseModel):
    """Weekly (7-day) usage data from Anthropic OAuth API."""
    utilization: float  # Percentage used (0-100)
    resets_at: Optional[str] = None  # ISO timestamp when limit resets

    @property
    def percentage(self) -> float:
        """Usage percentage (already provided by API)."""
        return min(100.0, max(0.0, self.utilization))

    @property
    def remaining_percentage(self) -> float:
        """Remaining percentage."""
        return max(0.0, 100.0 - self.utilization)

    @property
    def is_exceeded(self) -> bool:
        """Check if limit is exceeded (>= 100%)."""
        return self.utilization >= 100.0


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

    The API returns utilization percentages and reset timestamps for:
    - five_hour: 5-hour rolling session limit
    - seven_day: 7-day weekly limit

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

    # Required headers for the OAuth usage endpoint
    # The anthropic-beta header is REQUIRED for this endpoint to work
    headers = {
        "Authorization": f"Bearer {creds.access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "claude-code-agent/1.0.0",
        "anthropic-beta": "oauth-2025-04-20",  # Required beta header
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            logger.debug("oauth_usage_response",
                        status=response.status_code,
                        headers=dict(response.headers),
                        body_preview=response.text[:500] if response.text else None)

            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info("oauth_usage_raw_response", data=data)

                    # Parse the actual API response format:
                    # {
                    #   "five_hour": {"utilization": 6.0, "resets_at": "2025-11-04T04:59:59+00:00"},
                    #   "seven_day": {"utilization": 35.0, "resets_at": "2025-11-06T03:59:59+00:00"},
                    #   "seven_day_opus": {"utilization": 0.0, "resets_at": null},
                    #   ...
                    # }

                    result = OAuthUsageResponse()

                    # Parse five_hour (session) usage
                    five_hour = data.get("five_hour")
                    if five_hour and isinstance(five_hour, dict):
                        try:
                            result.session = SessionUsage(
                                utilization=float(five_hour.get("utilization", 0.0)),
                                resets_at=five_hour.get("resets_at")
                            )
                        except Exception as e:
                            logger.warning("failed_to_parse_five_hour_usage", error=str(e), data=five_hour)

                    # Parse seven_day (weekly) usage
                    seven_day = data.get("seven_day")
                    if seven_day and isinstance(seven_day, dict):
                        try:
                            result.weekly = WeeklyUsage(
                                utilization=float(seven_day.get("utilization", 0.0)),
                                resets_at=seven_day.get("resets_at")
                            )
                        except Exception as e:
                            logger.warning("failed_to_parse_seven_day_usage", error=str(e), data=seven_day)

                    if result.is_available:
                        logger.info("oauth_usage_fetched",
                                   has_session=result.session is not None,
                                   has_weekly=result.weekly is not None,
                                   session_util=result.session.utilization if result.session else None,
                                   weekly_util=result.weekly.utilization if result.weekly else None)
                        return result
                    else:
                        # Response was 200 but no usable data
                        return OAuthUsageResponse(
                            error=f"API returned success but no usage data. Response: {json.dumps(data)[:200]}"
                        )

                except json.JSONDecodeError as e:
                    logger.error("invalid_json_response", error=str(e), text=response.text[:500])
                    return OAuthUsageResponse(
                        error=f"Invalid JSON response from API: {str(e)}"
                    )

            elif response.status_code == 401:
                logger.warning("oauth_usage_auth_failed", status=401)
                return OAuthUsageResponse(
                    error="Authentication failed (401). Token may be invalid or expired. Try re-authenticating with Claude Code CLI."
                )

            elif response.status_code == 403:
                logger.warning("oauth_usage_forbidden", status=403, body=response.text[:300])
                return OAuthUsageResponse(
                    error="Access forbidden (403). Anthropic may have blocked this request. Ensure you're using official Claude Code OAuth tokens."
                )

            elif response.status_code == 404:
                return OAuthUsageResponse(
                    error="Usage endpoint not found (404). The API endpoint may have changed."
                )

            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                except Exception:
                    error_msg = f"HTTP {response.status_code}: {response.text[:300]}"

                logger.warning("oauth_usage_request_failed", status=response.status_code, error=error_msg)
                return OAuthUsageResponse(error=error_msg)

    except httpx.TimeoutException:
        logger.warning("oauth_usage_timeout")
        return OAuthUsageResponse(error="Request timed out. Anthropic API may be slow or unavailable.")

    except httpx.ConnectError as e:
        logger.error("oauth_usage_connect_error", error=str(e))
        return OAuthUsageResponse(error=f"Connection error: {str(e)}")

    except Exception as e:
        logger.error("oauth_usage_unexpected_error", error=str(e), error_type=type(e).__name__)
        return OAuthUsageResponse(error=f"Unexpected error: {str(e)}")
