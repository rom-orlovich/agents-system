"""Credentials management API endpoints."""

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_session as get_db_session, async_session_factory
from core.database.models import SessionDB
from core.cli_access import test_cli_access
from core.oauth_usage import fetch_oauth_usage, OAuthUsageResponse
from shared.machine_models import ClaudeCredentials, AuthStatus, CLIStatusUpdateMessage
from shared import APIResponse
import structlog

logger = structlog.get_logger()

def get_ws_hub(request: Request):
    """Get WebSocket hub from app state."""
    return request.app.state.ws_hub

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialStatus(str, Enum):
    """Credential status enum."""
    VALID = "valid"
    MISSING = "missing"
    EXPIRED = "expired"
    REFRESH_NEEDED = "refresh_needed"
    RATE_LIMITED = "rate_limited"
    CLI_UNAVAILABLE = "cli_unavailable"


class CredentialStatusResponse(BaseModel):
    """Credential status response."""
    status: CredentialStatus
    message: str
    cli_available: bool
    cli_version: Optional[str] = None
    expires_at: Optional[str] = None
    account_email: Optional[str] = None
    account_id: Optional[str] = None


@router.get("/status")
async def get_credential_status() -> CredentialStatusResponse:
    """Check credential and CLI status."""
    
    # 1. Check if Claude CLI is available
    cli_available = False
    cli_version = None
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.returncode == 0:
            cli_available = True
            cli_version = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 2. Check if credentials file exists
    creds_path = settings.credentials_path
    file_exists = creds_path.exists()
    
    if file_exists:
        try:
            creds_data = json.loads(creds_path.read_text())
            creds = ClaudeCredentials.from_dict(creds_data)
            
            status = CredentialStatus.VALID
            message = "Credentials valid"
            
            if creds.is_expired:
                status = CredentialStatus.EXPIRED
                message = "Credentials expired"
            elif creds.needs_refresh:
                status = CredentialStatus.REFRESH_NEEDED
                message = "Credentials expiring soon"
                
            return CredentialStatusResponse(
                status=status,
                message=message,
                cli_available=cli_available,
                cli_version=cli_version,
                expires_at=creds.expires_at_datetime.isoformat() if hasattr(creds, 'expires_at_datetime') else None,
                account_email=creds.email if hasattr(creds, 'email') else None,
                account_id=creds.account_id if hasattr(creds, 'account_id') else None,
            )
        except Exception as e:
            logger.error("credential_validation_error", error=str(e))
            # Fall through if file is corrupt but CLI exists
    
    # 3. Handle CLI-only state or Missing state
    if not cli_available:
        return CredentialStatusResponse(
            status=CredentialStatus.CLI_UNAVAILABLE,
            message="Claude CLI not installed and no credentials file found",
            cli_available=False,
        )
    
    return CredentialStatusResponse(
        status=CredentialStatus.MISSING,
        message="No credentials file found. CLI available for manual auth.",
        cli_available=True,
        cli_version=cli_version,
    )


@router.post("/upload")
async def upload_credentials(
    request: Request,
    file: UploadFile = File(..., description="claude.json credentials file")
) -> APIResponse:
    """Upload credentials file.
    
    Accepts credentials in either format:
    1. Direct format: {"access_token": "...", "refresh_token": "...", ...}
    2. Wrapped format: {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...", ...}}
    """
    
    if not file.filename.endswith('.json'):
        raise HTTPException(400, "File must be a JSON file")
    
    content = await file.read()
    try:
        creds_data = json.loads(content)
        creds = ClaudeCredentials.from_dict(creds_data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON file")
    except Exception as e:
        raise HTTPException(400, f"Invalid credentials format: {str(e)}")
    
    if creds.is_expired:
        raise HTTPException(400, "Credentials are already expired")
    
    # Save to persistent storage (for API use)
    creds_path = settings.credentials_path
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_bytes(content)

    # Also save to Claude CLI's expected location (for CLI use)
    cli_creds_path = Path.home() / ".claude" / "claude.json"
    cli_creds_path.parent.mkdir(parents=True, exist_ok=True)
    cli_creds_path.write_bytes(content)

    logger.info("credentials_uploaded",
                expires_at=creds.expires_at_datetime.isoformat(),
                api_path=str(creds_path),
                cli_path=str(cli_creds_path))
    
    # After successful upload, run test and update session status
    user_id = creds.account_id
    is_active = False
    
    # Generate user_id from access token if not present
    if not user_id:
        token_hash = hashlib.sha256(creds.access_token.encode()).hexdigest()[:16]
        user_id = f"user-{token_hash}"

    try:
        is_active = await test_cli_access()
        logger.info("CLI test completed after upload", active=is_active, user_id=user_id)
    except Exception as test_error:
        logger.warning("CLI test failed after upload", error=str(test_error))
        is_active = False
    
    if user_id:
        try:
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
                logger.info("CLI status updated in database", user_id=user_id, active=is_active)
            
            try:
                if request:
                    ws_hub = get_ws_hub(request)
                    if ws_hub:
                        await ws_hub.broadcast(
                            CLIStatusUpdateMessage(session_id=None, active=is_active)
                        )
                        logger.info("Broadcast CLI status update via WebSocket", active=is_active)
            except Exception as ws_error:
                logger.warning("Failed to broadcast CLI status update", error=str(ws_error))
        except Exception as db_error:
            logger.warning("Failed to update CLI status in database", error=str(db_error))
    
    return APIResponse(
        success=True,
        message="Credentials uploaded successfully",
        data={"expires_at": creds.expires_at_datetime.isoformat()}
    )


class AccountInfo(BaseModel):
    """Account information from database."""
    user_id: str
    session_count: int
    total_tasks: int
    total_cost_usd: float
    first_seen: str
    last_seen: str


@router.get("/cli-status")
async def get_cli_status(db: AsyncSession = Depends(get_db_session)):
    creds_path = settings.credentials_path
    cli_creds_path = Path.home() / ".claude" / "claude.json"

    if creds_path.exists():
        active_path = creds_path
    elif cli_creds_path.exists():
        active_path = cli_creds_path
    else:
        return {"active": False, "message": "Credentials not found (checked /data/credentials/ and ~/.claude/)"}

    try:
        creds_data = json.loads(active_path.read_text())
        creds = ClaudeCredentials.from_dict(creds_data)
        user_id = creds.account_id

        if not user_id:
            token_hash = hashlib.sha256(creds.access_token.encode()).hexdigest()[:16]
            user_id = f"user-{token_hash}"
        
        result = await db.execute(
            select(SessionDB)
            .where(SessionDB.user_id == user_id)
            .order_by(SessionDB.connected_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        
        if session:
            return {"active": session.active, "message": None}
        else:
            return {"active": False, "message": "No session found - upload credentials to test CLI"}
    except Exception as e:
        logger.warning("Failed to get CLI status", error=str(e))
        return {"active": False, "message": str(e)}


@router.get("/usage")
async def get_oauth_usage() -> dict:
    """
    Get Claude Code CLI OAuth usage limits (session and weekly).

    Returns usage data from Anthropic's OAuth usage endpoint:
    - session (five_hour): 5-hour rolling session usage limit
    - weekly (seven_day): 7-day weekly usage limit

    The API returns utilization percentages (0-100) and reset timestamps.
    """
    usage = await fetch_oauth_usage()

    if usage.error:
        return {
            "success": False,
            "error": usage.error,
            "session": None,
            "weekly": None,
        }

    result = {
        "success": True,
        "error": None,
    }

    if usage.session:
        result["session"] = {
            "utilization": round(usage.session.utilization, 2),
            "percentage": round(usage.session.percentage, 2),
            "remaining_percentage": round(usage.session.remaining_percentage, 2),
            "is_exceeded": usage.session.is_exceeded,
            "resets_at": usage.session.resets_at,
        }
    else:
        result["session"] = None

    if usage.weekly:
        result["weekly"] = {
            "utilization": round(usage.weekly.utilization, 2),
            "percentage": round(usage.weekly.percentage, 2),
            "remaining_percentage": round(usage.weekly.remaining_percentage, 2),
            "is_exceeded": usage.weekly.is_exceeded,
            "resets_at": usage.weekly.resets_at,
        }
    else:
        result["weekly"] = None

    return result


@router.get("/accounts")
async def list_accounts(db: AsyncSession = Depends(get_db_session)) -> List[AccountInfo]:
    """List all user accounts from database sessions."""
    
    # Query unique users with aggregated stats
    query = select(
        SessionDB.user_id,
        func.count(SessionDB.session_id).label('session_count'),
        func.sum(SessionDB.total_tasks).label('total_tasks'),
        func.sum(SessionDB.total_cost_usd).label('total_cost_usd'),
        func.min(SessionDB.connected_at).label('first_seen'),
        func.max(SessionDB.connected_at).label('last_seen')
    ).group_by(SessionDB.user_id)
    
    result = await db.execute(query)
    accounts = []
    
    for row in result:
        accounts.append(AccountInfo(
            user_id=row.user_id,
            session_count=row.session_count or 0,
            total_tasks=row.total_tasks or 0,
            total_cost_usd=row.total_cost_usd or 0.0,
            first_seen=row.first_seen.isoformat() if row.first_seen else "",
            last_seen=row.last_seen.isoformat() if row.last_seen else ""
        ))
    
    return accounts
