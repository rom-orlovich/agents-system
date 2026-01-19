#!/usr/bin/env python3
"""Standalone token refresh script.

Run this via cron every 30 minutes:
    */30 * * * * /app/scripts/refresh-token.py >> /var/log/token-refresh.log 2>&1

Or as a Docker entrypoint background process.

Usage:
    python refresh-token.py           # Check and refresh if needed
    python refresh-token.py --check   # Just check status
    python refresh-token.py --refresh # Force refresh
    python refresh-token.py --sync-aws # Sync to AWS Secrets Manager
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add shared to path
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent
sys.path.insert(0, str(project_root))

from shared.token_manager import TokenManager
from shared.enums import TokenStatus


async def main() -> int:
    """Refresh token if needed.
    
    Returns:
        0 on success, 1 on failure
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Token refresh check...")
    
    manager = TokenManager()
    
    # Check current status
    status = await manager.check_status()
    print(f"  Current status: {status.value}")
    
    if status == TokenStatus.NOT_FOUND:
        print("  ❌ No credentials found!")
        print("  Run: claude login")
        return 1
    
    if status == TokenStatus.VALID:
        minutes_left = manager._credentials.minutes_until_expiry if manager._credentials else 0
        print(f"  ✅ Token valid for {minutes_left:.1f} more minutes")
        return 0
    
    # Needs refresh (NEEDS_REFRESH or EXPIRED)
    print("  🔄 Refreshing token...")
    result = await manager.refresh()
    
    if result.success:
        minutes_valid = result.credentials.minutes_until_expiry if result.credentials else 0
        print(f"  ✅ Token refreshed! Valid for {minutes_valid:.1f} minutes")
        
        # Sync to AWS if in production (check for AWS metadata or env var)
        in_aws = (
            os.path.exists("/var/run/secrets/aws") or
            os.environ.get("AWS_EXECUTION_ENV") or
            os.environ.get("ECS_CONTAINER_METADATA_URI")
        )
        
        if in_aws:
            print("  📤 Syncing to AWS Secrets Manager...")
            sync_success = await manager.sync_to_aws()
            if sync_success:
                print("  ✅ Synced to AWS")
            else:
                print("  ⚠️ AWS sync failed (non-critical)")
        
        return 0
    else:
        print(f"  ❌ Refresh failed: {result.error}")
        return 1


if __name__ == "__main__":
    # Check for command-line args
    if len(sys.argv) > 1:
        # Use the token_manager's main function for full CLI
        from shared.token_manager import main as token_manager_main
        exit_code = asyncio.run(token_manager_main())
    else:
        # Simple refresh check
        exit_code = asyncio.run(main())
    
    sys.exit(exit_code)
