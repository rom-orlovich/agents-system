"""Account and machine management API endpoints."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_session
from core.database.redis_client import redis_client
from core.database.models import AccountDB, MachineDB

router = APIRouter(prefix="/api/v2", tags=["accounts", "machines"])


class CredentialUploadRequest(BaseModel):
    """Request to upload credentials."""
    user_id: str = Field(..., description="User ID from credentials")
    email: Optional[str] = Field(None, description="User email")
    expires_at: Optional[str] = Field(None, description="Credential expiration datetime")


class MachineRegisterRequest(BaseModel):
    """Request to register a machine."""
    machine_id: str = Field(..., description="Unique machine identifier")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    account_id: Optional[str] = Field(None, description="Account to link to")


class MachineLinkRequest(BaseModel):
    """Request to link machine to account."""
    account_id: str = Field(..., description="Account ID to link to")


# ==================== Credentials ====================

@router.post("/credentials/upload", response_model=dict)
async def upload_credentials(
    request: CredentialUploadRequest,
    db: AsyncSession = Depends(get_session)
):
    """Upload credentials and register/update account."""
    # Check if account exists
    result = await db.execute(
        select(AccountDB).where(AccountDB.account_id == request.user_id)
    )
    existing = result.scalar_one_or_none()
    
    expires_at = None
    if request.expires_at:
        try:
            expires_at = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    if existing:
        # Update existing account
        existing.email = request.email or existing.email
        existing.credential_expires_at = expires_at
        existing.credential_status = "valid"
        existing.updated_at = datetime.now(timezone.utc)
        registered = False
    else:
        # Create new account
        account = AccountDB(
            account_id=request.user_id,
            email=request.email,
            credential_expires_at=expires_at,
            credential_status="valid"
        )
        db.add(account)
        registered = True
    
    await db.commit()
    
    return {
        "account_id": request.user_id,
        "registered": registered,
        "credential_status": "valid"
    }


# ==================== Accounts ====================

@router.get("/accounts", response_model=dict)
async def list_accounts(db: AsyncSession = Depends(get_session)):
    """List all registered accounts."""
    result = await db.execute(select(AccountDB))
    accounts = result.scalars().all()
    
    return {
        "accounts": [
            {
                "account_id": a.account_id,
                "email": a.email,
                "display_name": a.display_name,
                "credential_status": _get_credential_status(a),
                "credential_expires_at": a.credential_expires_at.isoformat() if a.credential_expires_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in accounts
        ]
    }


@router.get("/accounts/current", response_model=dict)
async def get_current_account(db: AsyncSession = Depends(get_session)):
    """Get current active account with machines."""
    # Get first valid account (in real implementation, this would be session-based)
    result = await db.execute(
        select(AccountDB).where(AccountDB.credential_status == "valid").limit(1)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        return {"account_id": None, "accounts": []}
    
    # Get machines for this account
    machines_result = await db.execute(
        select(MachineDB).where(MachineDB.account_id == account.account_id)
    )
    machines = machines_result.scalars().all()
    
    return {
        "account_id": account.account_id,
        "email": account.email,
        "display_name": account.display_name,
        "credential_status": _get_credential_status(account),
        "machines": [
            {
                "machine_id": m.machine_id,
                "display_name": m.display_name,
                "status": m.status
            }
            for m in machines
        ]
    }


@router.get("/accounts/{account_id}", response_model=dict)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get account details with machines."""
    result = await db.execute(
        select(AccountDB).where(AccountDB.account_id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # Get machines
    machines_result = await db.execute(
        select(MachineDB).where(MachineDB.account_id == account_id)
    )
    machines = machines_result.scalars().all()
    
    return {
        "account_id": account.account_id,
        "email": account.email,
        "display_name": account.display_name,
        "credential_status": _get_credential_status(account),
        "credential_expires_at": account.credential_expires_at.isoformat() if account.credential_expires_at else None,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "machines": [
            {
                "machine_id": m.machine_id,
                "display_name": m.display_name,
                "status": m.status,
                "last_heartbeat": m.last_heartbeat.isoformat() if m.last_heartbeat else None
            }
            for m in machines
        ]
    }


# ==================== Machines ====================

@router.get("/machines", response_model=dict)
async def list_machines(db: AsyncSession = Depends(get_session)):
    """List all machines."""
    result = await db.execute(select(MachineDB))
    machines = result.scalars().all()
    
    # Get active machines from Redis
    active_ids = await redis_client.get_active_machines()
    
    return {
        "machines": [
            {
                "machine_id": m.machine_id,
                "account_id": m.account_id,
                "display_name": m.display_name,
                "status": "online" if m.machine_id in active_ids else m.status,
                "last_heartbeat": m.last_heartbeat.isoformat() if m.last_heartbeat else None,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in machines
        ]
    }


@router.post("/machines/register", response_model=dict)
async def register_machine(
    request: MachineRegisterRequest,
    db: AsyncSession = Depends(get_session)
):
    """Register a new machine."""
    # Check if machine exists
    result = await db.execute(
        select(MachineDB).where(MachineDB.machine_id == request.machine_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing
        existing.status = "online"
        existing.last_heartbeat = datetime.now(timezone.utc)
        if request.display_name:
            existing.display_name = request.display_name
        if request.account_id:
            existing.account_id = request.account_id
    else:
        # Create new
        machine = MachineDB(
            machine_id=request.machine_id,
            account_id=request.account_id,
            display_name=request.display_name,
            status="online",
            last_heartbeat=datetime.now(timezone.utc)
        )
        db.add(machine)
    
    # Register in Redis
    await redis_client.register_machine(request.machine_id, request.account_id)
    
    await db.commit()
    
    return {
        "machine_id": request.machine_id,
        "status": "registered"
    }


@router.get("/machines/{machine_id}", response_model=dict)
async def get_machine(
    machine_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get machine details."""
    result = await db.execute(
        select(MachineDB).where(MachineDB.machine_id == machine_id)
    )
    machine = result.scalar_one_or_none()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} not found"
        )
    
    # Get real-time status from Redis
    redis_status = await redis_client.get_machine_status(machine_id)
    metrics = await redis_client.get_machine_metrics(machine_id)
    
    return {
        "machine_id": machine.machine_id,
        "account_id": machine.account_id,
        "display_name": machine.display_name,
        "status": redis_status.get("status", machine.status) if redis_status else machine.status,
        "last_heartbeat": redis_status.get("heartbeat") if redis_status else (
            machine.last_heartbeat.isoformat() if machine.last_heartbeat else None
        ),
        "metrics": metrics or {}
    }


@router.post("/machines/{machine_id}/heartbeat", response_model=dict)
async def machine_heartbeat(
    machine_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Update machine heartbeat."""
    # Update Redis
    await redis_client.update_machine_heartbeat(machine_id)
    
    # Update database
    result = await db.execute(
        select(MachineDB).where(MachineDB.machine_id == machine_id)
    )
    machine = result.scalar_one_or_none()
    
    if machine:
        machine.last_heartbeat = datetime.now(timezone.utc)
        await db.commit()
    
    return {"ok": True}


@router.post("/machines/{machine_id}/link", response_model=dict)
async def link_machine_to_account(
    machine_id: str,
    request: MachineLinkRequest,
    db: AsyncSession = Depends(get_session)
):
    """Link a machine to an account."""
    # Verify account exists
    account_result = await db.execute(
        select(AccountDB).where(AccountDB.account_id == request.account_id)
    )
    account = account_result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {request.account_id} not found"
        )
    
    # Get or create machine
    machine_result = await db.execute(
        select(MachineDB).where(MachineDB.machine_id == machine_id)
    )
    machine = machine_result.scalar_one_or_none()
    
    if not machine:
        machine = MachineDB(
            machine_id=machine_id,
            account_id=request.account_id,
            status="offline"
        )
        db.add(machine)
    else:
        machine.account_id = request.account_id
    
    await db.commit()
    
    return {
        "linked": True,
        "machine_id": machine_id,
        "account_id": request.account_id
    }


def _get_credential_status(account: AccountDB) -> str:
    """Determine credential status including expiring_soon."""
    if account.credential_status in ["expired", "revoked"]:
        return account.credential_status
    
    if account.credential_expires_at:
        # SQLite returns naive datetimes, convert to UTC-aware for comparison
        expires_at = account.credential_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        days_until_expiry = (expires_at - datetime.now(timezone.utc)).days
        if days_until_expiry < 0:
            return "expired"
        elif days_until_expiry <= 7:
            return "expiring_soon"
    
    return account.credential_status or "valid"
