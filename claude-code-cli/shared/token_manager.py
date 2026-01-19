"""Token management for Claude Code OAuth.

This module handles:
1. Reading OAuth credentials from ~/.claude/.credentials.json
2. Checking token expiration
3. Refreshing tokens before they expire
4. Syncing to AWS Secrets Manager (production)

Token Lifecycle:
    Hour 0:00 → Container starts, load tokens
    Hour 0:30 → Cron runs, check & refresh if needed
    Hour 1:00 → Token always valid, never expires!

Usage:
    from shared.token_manager import TokenManager
    
    manager = TokenManager()
    
    # Ensure token is valid before API call
    result = await manager.ensure_valid()
    if not result.success:
        print(f"Token error: {result.error}")
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional
import logging

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from .types import OAuthCredentials, TokenRefreshResult
from .enums import TokenStatus
from .constants import (
    CREDENTIALS_FILE,
    TOKEN_REFRESH_THRESHOLD_MINUTES,
    ANTHROPIC_TOKEN_URL,
    ANTHROPIC_CLIENT_ID,
    AWS_SECRET_NAME,
)

# Setup logging
logger = logging.getLogger("token_manager")


class TokenManager:
    """Manages OAuth tokens for Claude Code.
    
    This class handles the complete token lifecycle:
    1. Load credentials from file
    2. Check expiration status
    3. Refresh tokens when needed
    4. Save updated credentials
    5. Optionally sync to AWS Secrets Manager
    
    Attributes:
        credentials_path: Path to credentials file
        refresh_threshold_minutes: Minutes before expiry to trigger refresh
    
    Example:
        manager = TokenManager()
        
        # Check status
        status = await manager.check_status()
        print(f"Token status: {status}")
        
        # Refresh if needed
        if status == TokenStatus.NEEDS_REFRESH:
            result = await manager.refresh()
            if result.success:
                print("Token refreshed!")
    """
    
    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        refresh_threshold_minutes: int = TOKEN_REFRESH_THRESHOLD_MINUTES,
    ):
        """Initialize token manager.
        
        Args:
            credentials_path: Path to credentials file.
                            Defaults to ~/.claude/.credentials.json
            refresh_threshold_minutes: Minutes before expiry to trigger refresh.
        """
        self.credentials_path = credentials_path or CREDENTIALS_FILE
        self.refresh_threshold_minutes = refresh_threshold_minutes
        self._credentials: Optional[OAuthCredentials] = None
        
        # Ensure path is a Path object
        if isinstance(self.credentials_path, str):
            self.credentials_path = Path(self.credentials_path)
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    async def load_credentials(self) -> Optional[OAuthCredentials]:
        """Load credentials from file.
        
        Returns:
            OAuthCredentials if file exists and is valid, None otherwise.
        """
        if not self.credentials_path.exists():
            logger.warning(f"Credentials file not found: {self.credentials_path}")
            return None
        
        try:
            with open(self.credentials_path, "r") as f:
                data = json.load(f)
            
            # Handle both camelCase and snake_case
            if "accessToken" in data:
                self._credentials = OAuthCredentials.from_dict(data)
            elif "access_token" in data:
                self._credentials = OAuthCredentials(
                    access_token=data.get("access_token", ""),
                    refresh_token=data.get("refresh_token", ""),
                    expires_at=data.get("expires_at", 0),
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope", ""),
                )
            else:
                logger.error("Invalid credentials format - no access token found")
                return None
            
            logger.info(
                f"Loaded credentials, expires in {self._credentials.minutes_until_expiry:.1f} min"
            )
            return self._credentials
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid credentials file (JSON error): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None
    
    async def save_credentials(self, credentials: OAuthCredentials) -> bool:
        """Save credentials to file.
        
        Args:
            credentials: Credentials to save.
            
        Returns:
            True if save succeeded.
        """
        try:
            # Ensure directory exists
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.credentials_path, "w") as f:
                json.dump(credentials.to_dict(), f, indent=2)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.credentials_path, 0o600)
            
            self._credentials = credentials
            logger.info("Credentials saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    async def check_status(self) -> TokenStatus:
        """Check current token status.
        
        Returns:
            TokenStatus indicating current state.
        """
        credentials = await self.load_credentials()
        
        if credentials is None:
            return TokenStatus.NOT_FOUND
        
        if credentials.is_expired:
            return TokenStatus.EXPIRED
        
        if credentials.needs_refresh:
            return TokenStatus.NEEDS_REFRESH
        
        return TokenStatus.VALID
    
    async def refresh(self) -> TokenRefreshResult:
        """Refresh the access token.
        
        Uses the refresh_token to obtain a new access_token from Anthropic.
        
        Returns:
            TokenRefreshResult with success status and new credentials.
        """
        if not HAS_AIOHTTP:
            return TokenRefreshResult(
                success=False,
                error="aiohttp not installed - cannot refresh token",
                status=TokenStatus.REFRESH_FAILED,
            )
        
        if self._credentials is None:
            await self.load_credentials()
        
        if self._credentials is None:
            return TokenRefreshResult(
                success=False,
                error="No credentials to refresh",
                status=TokenStatus.NOT_FOUND,
            )
        
        if not self._credentials.refresh_token:
            return TokenRefreshResult(
                success=False,
                error="No refresh token available",
                status=TokenStatus.REFRESH_FAILED,
            )
        
        if self._credentials.is_expired:
            logger.warning("Token is expired, refresh may fail")
        
        logger.info("Refreshing access token...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ANTHROPIC_TOKEN_URL,
                    json={
                        "grant_type": "refresh_token",
                        "refresh_token": self._credentials.refresh_token,
                        "client_id": ANTHROPIC_CLIENT_ID,
                    },
                    headers={
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Token refresh failed: {response.status} - {error_text}")
                        return TokenRefreshResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}",
                            status=TokenStatus.REFRESH_FAILED,
                        )
                    
                    data = await response.json()
                    
                    # Calculate new expiry time
                    expires_in = data.get("expires_in", 3600)  # Default 1 hour
                    expires_at = int(time.time() * 1000) + (expires_in * 1000)
                    
                    # Create new credentials
                    # Use new refresh token if provided, otherwise keep old one
                    new_credentials = OAuthCredentials(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token", self._credentials.refresh_token),
                        expires_at=expires_at,
                        token_type=data.get("token_type", "Bearer"),
                        scope=data.get("scope", self._credentials.scope),
                    )
                    
                    # Save to file
                    await self.save_credentials(new_credentials)
                    
                    logger.info(
                        f"Token refreshed! New expiry in {new_credentials.minutes_until_expiry:.1f} min"
                    )
                    
                    return TokenRefreshResult(
                        success=True,
                        credentials=new_credentials,
                        status=TokenStatus.REFRESHED,
                    )
                    
        except asyncio.TimeoutError:
            logger.error("Token refresh timed out")
            return TokenRefreshResult(
                success=False,
                error="Request timed out",
                status=TokenStatus.REFRESH_FAILED,
            )
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during refresh: {e}")
            return TokenRefreshResult(
                success=False,
                error=f"HTTP error: {e}",
                status=TokenStatus.REFRESH_FAILED,
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return TokenRefreshResult(
                success=False,
                error=str(e),
                status=TokenStatus.REFRESH_FAILED,
            )
    
    async def ensure_valid(self) -> TokenRefreshResult:
        """Ensure token is valid, refreshing if needed.
        
        This is the main entry point for token management.
        Call this before making API calls to ensure a valid token.
        
        Returns:
            TokenRefreshResult with current status.
        """
        status = await self.check_status()
        
        if status == TokenStatus.VALID:
            return TokenRefreshResult(
                success=True,
                credentials=self._credentials,
                status=status,
            )
        
        if status in (TokenStatus.NEEDS_REFRESH, TokenStatus.EXPIRED):
            return await self.refresh()
        
        return TokenRefreshResult(
            success=False,
            error=f"Cannot ensure valid token: {status.value}",
            status=status,
        )
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token if available.
        
        Returns:
            Access token string or None.
        """
        if self._credentials:
            return self._credentials.access_token
        return None
    
    # =========================================================================
    # AWS Secrets Manager Integration (Production)
    # =========================================================================
    
    async def sync_to_aws(self, secret_name: str = AWS_SECRET_NAME) -> bool:
        """Sync credentials to AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in AWS.
            
        Returns:
            True if sync succeeded.
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            logger.warning("boto3 not installed, skipping AWS sync")
            return False
        
        if self._credentials is None:
            await self.load_credentials()
        
        if self._credentials is None:
            logger.error("No credentials to sync")
            return False
        
        try:
            client = boto3.client("secretsmanager")
            secret_value = json.dumps(self._credentials.to_dict())
            
            try:
                client.update_secret(
                    SecretId=secret_name,
                    SecretString=secret_value,
                )
                logger.info(f"Credentials updated in AWS: {secret_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    client.create_secret(
                        Name=secret_name,
                        SecretString=secret_value,
                    )
                    logger.info(f"Credentials created in AWS: {secret_name}")
                else:
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"AWS sync failed: {e}")
            return False
    
    async def load_from_aws(self, secret_name: str = AWS_SECRET_NAME) -> bool:
        """Load credentials from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in AWS.
            
        Returns:
            True if load succeeded.
        """
        try:
            import boto3
        except ImportError:
            logger.warning("boto3 not installed")
            return False
        
        try:
            client = boto3.client("secretsmanager")
            
            response = client.get_secret_value(SecretId=secret_name)
            data = json.loads(response["SecretString"])
            
            self._credentials = OAuthCredentials.from_dict(data)
            
            # Save locally
            await self.save_credentials(self._credentials)
            
            logger.info(f"Credentials loaded from AWS: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"AWS load failed: {e}")
            return False


# =============================================================================
# STANDALONE SCRIPT FUNCTIONS
# =============================================================================

async def main() -> int:
    """Main function for standalone execution.
    
    This is called by the cron job every 30 minutes.
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    import argparse
    
    # Setup logging for standalone use
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    parser = argparse.ArgumentParser(description="Claude Code Token Manager")
    parser.add_argument("--check", action="store_true", help="Check token status")
    parser.add_argument("--refresh", action="store_true", help="Force refresh token")
    parser.add_argument("--sync-aws", action="store_true", help="Sync to AWS Secrets Manager")
    parser.add_argument("--load-aws", action="store_true", help="Load from AWS Secrets Manager")
    
    args = parser.parse_args()
    
    manager = TokenManager()
    
    if args.check:
        status = await manager.check_status()
        print(f"Token status: {status.value}")
        if manager._credentials:
            print(f"Expires in: {manager._credentials.minutes_until_expiry:.1f} minutes")
            print(f"Expires at: {manager._credentials.expires_at_datetime}")
        return 0
    
    if args.refresh:
        result = await manager.refresh()
        if result.success:
            print("✅ Token refreshed!")
            print(f"New expiry: {result.credentials.expires_at_datetime}")
            return 0
        else:
            print(f"❌ Refresh failed: {result.error}")
            return 1
    
    if args.sync_aws:
        success = await manager.sync_to_aws()
        print("✅ Synced to AWS" if success else "❌ Sync failed")
        return 0 if success else 1
    
    if args.load_aws:
        success = await manager.load_from_aws()
        print("✅ Loaded from AWS" if success else "❌ Load failed")
        return 0 if success else 1
    
    # Default: ensure valid (used by cron)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Token refresh check...")
    
    result = await manager.ensure_valid()
    
    if result.success:
        status_msg = "refreshed" if result.status == TokenStatus.REFRESHED else "valid"
        print(f"✅ Token {status_msg}")
        if result.credentials:
            print(f"   Expires in: {result.credentials.minutes_until_expiry:.1f} min")
        return 0
    else:
        print(f"❌ Token invalid: {result.error}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
