#!/usr/bin/env python3
"""
Test CLI after Docker build and update status in database.
This script runs inside the container after build to verify CLI is working.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.cli_access import test_cli_access
from core.database import init_db, async_session_factory
from core.database.models import SessionDB
from core.config import settings
from shared.machine_models import ClaudeCredentials
from sqlalchemy import select, update
import structlog

logger = structlog.get_logger()


async def test_cli_and_update_status():
    """Test CLI access and update database status."""
    try:
        # Initialize database
        await init_db()
        
        # Check if credentials exist
        creds_path = settings.credentials_path
        if not creds_path.exists():
            logger.info("No credentials found - skipping CLI test")
            return 0
        
        # Load credentials
        creds_data = json.loads(creds_path.read_text())
        creds = ClaudeCredentials.from_dict(creds_data)
        user_id = creds.account_id
        
        # Generate user_id from access token if not present
        if not user_id:
            import hashlib
            token_hash = hashlib.sha256(creds.access_token.encode()).hexdigest()[:16]
            user_id = f"user-{token_hash}"
        
        # Test CLI access
        logger.info("Testing CLI access after Docker build", user_id=user_id)
        is_active = await test_cli_access()
        
        # Update or create session for this user
        async with async_session_factory() as session:
            # Check if session exists for this user_id
            result = await session.execute(
                select(SessionDB)
                .where(SessionDB.user_id == user_id)
                .order_by(SessionDB.connected_at.desc())
                .limit(1)
            )
            existing_session = result.scalar_one_or_none()
            
            if existing_session:
                # Update existing session
                await session.execute(
                    update(SessionDB)
                    .where(SessionDB.session_id == existing_session.session_id)
                    .values(active=is_active)
                )
            else:
                # Create new session if none exists
                session_id = f"cred-{uuid.uuid4().hex[:12]}"
                new_session = SessionDB(
                    session_id=session_id,
                    user_id=user_id,
                    machine_id="claude-agent-001",
                    connected_at=datetime.now(timezone.utc),
                    active=is_active
                )
                session.add(new_session)
            
            await session.commit()
        
        logger.info("CLI test completed after build", active=is_active, user_id=user_id)
        return 0 if is_active else 1
        
    except Exception as e:
        logger.error("CLI test failed after build", error=str(e))
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_cli_and_update_status())
    sys.exit(exit_code)
