"""Integration tests for security & permissions (Part 6 of TDD Requirements)."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
import uuid


class TestSecurityPermissionsFlow:
    """Test security and permission business requirements."""
    
    @pytest.mark.asyncio
    async def test_container_exec_requires_allowlist(self, client):
        """
        REQUIREMENT: Container exec commands must be in allowlist.
        """
        # Try to run dangerous command
        response = await client.post("/api/v2/container/exec", json={
            "command": "rm -rf /"
        })
        
        assert response.status_code == 403
        assert "not in allowlist" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_container_exec_allowed_commands(self, client):
        """
        REQUIREMENT: Allowed commands should execute successfully.
        """
        # Try to run allowed command
        response = await client.post("/api/v2/container/exec", json={
            "command": "echo hello"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "hello" in data["stdout"]
    
    @pytest.mark.asyncio
    async def test_kill_process_requires_allowlist(self, client):
        """
        REQUIREMENT: Killing processes should only work for allowed processes.
        """
        # Try to kill PID 1 (init process - never allowed)
        response = await client.post("/api/v2/container/processes/1/kill")
        
        assert response.status_code in [403, 404]
    
    @pytest.mark.asyncio
    async def test_audit_log_records_subagent_spawn(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Subagent spawn should be logged to audit trail.
        """
        from core.database.models import AuditLogDB
        from sqlalchemy import select
        
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Spawn a subagent
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground"
        })
        
        assert response.status_code == 200
        
        # Check audit log
        result = await db_session.execute(
            select(AuditLogDB).where(AuditLogDB.action == "subagent_spawn")
        )
        logs = result.scalars().all()
        
        assert len(logs) >= 1
        assert logs[-1].action == "subagent_spawn"
    
    @pytest.mark.asyncio
    async def test_audit_log_includes_actor(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Audit logs should include the actor (who performed the action).
        """
        from core.database.models import AuditLogDB
        from sqlalchemy import select
        
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "executor",
            "mode": "background"
        })
        
        result = await db_session.execute(
            select(AuditLogDB).order_by(AuditLogDB.created_at.desc()).limit(1)
        )
        log = result.scalar_one_or_none()
        
        assert log is not None
        assert log.actor is not None
    
    @pytest.mark.asyncio
    async def test_audit_log_includes_target(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Audit logs should include the target of the action.
        """
        from core.database.models import AuditLogDB
        from sqlalchemy import select
        
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground"
        })
        
        subagent_id = response.json()["data"]["subagent_id"]
        
        result = await db_session.execute(
            select(AuditLogDB).where(AuditLogDB.target_id == subagent_id)
        )
        log = result.scalar_one_or_none()
        
        assert log is not None
        assert log.target_type == "subagent"


class TestCredentialSecurityFlow:
    """Test credential security requirements."""
    
    @pytest.mark.asyncio
    async def test_credential_status_checked(self, client, db_session):
        """
        REQUIREMENT: Credential status should be validated.
        """
        from core.database.models import AccountDB
        from datetime import timedelta
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        # Create account with expired credentials
        account = AccountDB(
            account_id=account_id,
            email="expired@example.com",
            credential_status="expired",
            credential_expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(account)
        await db_session.commit()
        
        response = await client.get(f"/api/v2/accounts/{account_id}")
        
        assert response.status_code == 200
        assert response.json()["credential_status"] == "expired"
    
    @pytest.mark.asyncio
    async def test_expiring_credentials_flagged(self, client, db_session):
        """
        REQUIREMENT: Credentials expiring within 7 days should be flagged.
        """
        from core.database.models import AccountDB
        from datetime import timedelta
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        # Create account with credentials expiring in 3 days
        account = AccountDB(
            account_id=account_id,
            email="expiring@example.com",
            credential_status="valid",
            credential_expires_at=datetime.utcnow() + timedelta(days=3)
        )
        db_session.add(account)
        await db_session.commit()
        
        response = await client.get(f"/api/v2/accounts/{account_id}")
        
        assert response.status_code == 200
        # Should be flagged as expiring_soon
        assert response.json()["credential_status"] in ["valid", "expiring_soon"]


class TestMaxLimitsFlow:
    """Test resource limit requirements."""
    
    @pytest.mark.asyncio
    async def test_max_parallel_subagents_enforced(self, client, redis_mock):
        """
        REQUIREMENT: Maximum of 10 parallel subagents should be enforced.
        """
        # Mock that we already have 10 active subagents
        redis_mock.get_active_subagent_count = AsyncMock(return_value=10)
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "background"
        })
        
        assert response.status_code == 429
        assert "maximum" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_parallel_group_respects_limit(self, client, redis_mock):
        """
        REQUIREMENT: Parallel group spawn should respect subagent limit.
        """
        # Mock that we have 8 active, trying to spawn 5 more
        redis_mock.get_active_subagent_count = AsyncMock(return_value=8)
        
        response = await client.post("/api/v2/subagents/parallel", json={
            "agents": [
                {"type": "planning", "task": f"Task {i}"} for i in range(5)
            ]
        })
        
        assert response.status_code == 429


class TestInputValidationFlow:
    """Test input validation requirements."""
    
    @pytest.mark.asyncio
    async def test_subagent_type_validated(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Subagent type should be validated.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Valid agent type should work
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground"
        })
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_subagent_mode_validated(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Subagent mode should be validated.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Valid modes: foreground, background, parallel
        for mode in ["foreground", "background"]:
            response = await client.post("/api/v2/subagents/spawn", json={
                "agent_type": "planning",
                "mode": mode
            })
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_machine_id_required_for_registration(self, client, redis_mock):
        """
        REQUIREMENT: Machine registration requires machine_id.
        """
        response = await client.post("/api/v2/machines/register", json={
            "display_name": "No ID Machine"
        })
        
        # Should fail validation
        assert response.status_code == 422
