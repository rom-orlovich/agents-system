"""Credentials management API endpoints."""

import json
import subprocess
from enum import Enum
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel

from core.config import settings
from shared.machine_models import ClaudeCredentials, AuthStatus
from shared import APIResponse
import structlog

logger = structlog.get_logger()

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
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5,
            text=True
        )
        cli_available = result.returncode == 0
        cli_version = result.stdout.strip() if cli_available else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CredentialStatusResponse(
            status=CredentialStatus.CLI_UNAVAILABLE,
            message="Claude CLI not found in container",
            cli_available=False,
        )
    
    # 2. Check if credentials file exists
    creds_path = settings.credentials_path
    if not creds_path.exists():
        return CredentialStatusResponse(
            status=CredentialStatus.MISSING,
            message="Credentials file not found. Please upload claude.json",
            cli_available=True,
            cli_version=cli_version,
        )
    
    # 3. Parse and validate credentials
    try:
        creds_data = json.loads(creds_path.read_text())
        creds = ClaudeCredentials(**creds_data)
        
        if creds.is_expired:
            return CredentialStatusResponse(
                status=CredentialStatus.EXPIRED,
                message="Credentials expired",
                cli_available=True,
                cli_version=cli_version,
            )
        
        if creds.needs_refresh:
            return CredentialStatusResponse(
                status=CredentialStatus.REFRESH_NEEDED,
                message="Credentials expiring soon",
                cli_available=True,
                cli_version=cli_version,
                expires_at=creds.expires_at_datetime.isoformat(),
            )
        
        return CredentialStatusResponse(
            status=CredentialStatus.VALID,
            message="Credentials valid",
            cli_available=True,
            cli_version=cli_version,
            expires_at=creds.expires_at_datetime.isoformat(),
            account_email=creds.email,
            account_id=creds.user_id,
        )
    except Exception as e:
        logger.error("credential_validation_error", error=str(e))
        return CredentialStatusResponse(
            status=CredentialStatus.MISSING,
            message=f"Invalid credentials file: {str(e)}",
            cli_available=True,
            cli_version=cli_version,
        )


@router.post("/upload")
async def upload_credentials(
    file: UploadFile = File(..., description="claude.json credentials file")
) -> APIResponse:
    """Upload credentials file."""
    
    if not file.filename.endswith('.json'):
        raise HTTPException(400, "File must be a JSON file")
    
    content = await file.read()
    try:
        creds_data = json.loads(content)
        creds = ClaudeCredentials(**creds_data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON file")
    except Exception as e:
        raise HTTPException(400, f"Invalid credentials format: {str(e)}")
    
    if creds.is_expired:
        raise HTTPException(400, "Credentials are already expired")
    
    # Save to persistent storage
    creds_path = settings.credentials_path
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file synchronously (aiofiles not required for small files)
    creds_path.write_bytes(content)
    
    logger.info("credentials_uploaded", expires_at=creds.expires_at_datetime.isoformat())
    
    return APIResponse(
        success=True,
        message="Credentials uploaded successfully",
        data={"expires_at": creds.expires_at_datetime.isoformat()}
    )
