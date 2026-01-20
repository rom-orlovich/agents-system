#!/usr/bin/env python3
"""Ensure Claude OAuth authentication is valid.

This script is called by entrypoint.sh to:
1. Check if OAuth credentials exist
2. Auto-refresh tokens if expired or about to expire
3. Exit with proper status code for shell script handling

Exit Codes:
    0 = Authentication OK (token valid or refreshed)
    1 = Authentication failed (no credentials or refresh failed)
    2 = Fallback to API key (no OAuth, but ANTHROPIC_API_KEY is set)

Usage:
    python -m shared.ensure_auth
    
    # Or directly:
    python shared/ensure_auth.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports when run directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.token_manager import TokenManager
from shared.enums import TokenStatus


async def ensure_auth() -> int:
    """Ensure OAuth authentication is valid.
    
    Returns:
        Exit code (0=OK, 1=Failed, 2=Fallback to API key)
    """
    # Check for OAuth credentials file
    creds_path = Path(os.path.expanduser("~/.claude/.credentials.json"))
    
    if not creds_path.exists():
        print("⚠️  No OAuth credentials file found")
        
        # Check for API key fallback
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("✅ Falling back to ANTHROPIC_API_KEY")
            return 2  # Fallback to API key
        
        print("❌ No authentication method available")
        return 1
    
    print("🔐 OAuth credentials file found")
    print("🔄 Checking token validity...")
    
    # Use TokenManager to check and refresh
    manager = TokenManager(credentials_path=creds_path)
    
    # Load and check status
    status = await manager.check_status()
    
    print(f"📊 Token status: {status.value}")
    
    if status == TokenStatus.VALID:
        if manager._credentials:
            print(f"✅ Token valid for {manager._credentials.minutes_until_expiry:.1f} more minutes")
        return 0
    
    if status == TokenStatus.NOT_FOUND:
        print("❌ Credentials file exists but is invalid")
        return 1
    
    if status in (TokenStatus.EXPIRED, TokenStatus.NEEDS_REFRESH):
        print("🔄 Token needs refresh, attempting auto-refresh...")
        
        result = await manager.refresh()
        
        if result.success:
            print("✅ Token refreshed successfully!")
            if result.credentials:
                print(f"   New expiry: {result.credentials.minutes_until_expiry:.1f} minutes")
            return 0
        else:
            print(f"❌ Token refresh failed: {result.error}")
            print("")
            print("💡 The refresh token may have expired. Please run on host:")
            print("   claude login")
            print("   ./infrastructure/docker/extract-oauth.sh")
            return 1
    
    # Unknown status
    print(f"❌ Unknown token status: {status}")
    return 1


def main() -> int:
    """Main entry point."""
    return asyncio.run(ensure_auth())


if __name__ == "__main__":
    sys.exit(main())
