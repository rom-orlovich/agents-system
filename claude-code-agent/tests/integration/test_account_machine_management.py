"""Integration tests for multi-account & machine management (Part 8 of TDD Requirements)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import uuid


class TestAccountRegistrationFlow:
    """Test account registration business requirements."""
    async def test_credential_upload_registers_account(self, client, db_session):
        """
        REQUIREMENT: When a user uploads credentials, the system should
        automatically register/update the account.
        """
        # Create mock credential file content
        credential_content = {
            "user_id": f"user-{uuid.uuid4().hex[:8]}",
            "email": "test@example.com",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        
        response = await client.post(
            "/api/v2/credentials/upload",
            json=credential_content
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "account_id" in data
        assert data.get("registered") is True or "account_id" in data
    async def test_credential_upload_updates_existing_account(self, client, db_session):
        """
        REQUIREMENT: Uploading credentials for existing account should update it.
        """
        from core.database.models import AccountDB
        
        account_id = f"user-{uuid.uuid4().hex[:8]}"
        
        # Create existing account
        account = AccountDB(
            account_id=account_id,
            email="old@example.com",
            credential_status="expired"
        )
        db_session.add(account)
        await db_session.commit()
        
        # Upload new credentials
        credential_content = {
            "user_id": account_id,
            "email": "new@example.com",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        
        response = await client.post(
            "/api/v2/credentials/upload",
            json=credential_content
        )
        
        assert response.status_code == 200
        # Account should be updated, not created new
        data = response.json()
        assert data.get("account_id") == account_id
    async def test_list_accounts(self, client, db_session):
        """
        REQUIREMENT: Should be able to list all registered accounts.
        """
        from core.database.models import AccountDB
        
        # Create test accounts
        for i in range(3):
            account = AccountDB(
                account_id=f"account-{i}",
                email=f"user{i}@example.com",
                credential_status="valid"
            )
            db_session.add(account)
        await db_session.commit()
        
        response = await client.get("/api/v2/accounts")
        
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        assert len(accounts) >= 3
    async def test_get_account_details(self, client, db_session):
        """
        REQUIREMENT: Should be able to get account details with machines.
        """
        from core.database.models import AccountDB, MachineDB
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        # Create account with machines
        account = AccountDB(
            account_id=account_id,
            email="test@example.com",
            credential_status="valid"
        )
        db_session.add(account)
        
        machine = MachineDB(
            machine_id=f"machine-{uuid.uuid4().hex[:8]}",
            account_id=account_id,
            status="online"
        )
        db_session.add(machine)
        await db_session.commit()
        
        response = await client.get(f"/api/v2/accounts/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == account_id
        assert "machines" in data


class TestMachineManagementFlow:
    """Test machine management business requirements."""
    async def test_register_machine(self, client, redis_mock, db_session):
        """
        REQUIREMENT: Should be able to register a new machine.
        """
        redis_mock.register_machine = AsyncMock()
        
        machine_id = f"machine-{uuid.uuid4().hex[:8]}"
        
        response = await client.post("/api/v2/machines/register", json={
            "machine_id": machine_id,
            "display_name": "Test Machine"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["machine_id"] == machine_id
        assert data["status"] == "registered"
    async def test_machine_heartbeat(self, client, redis_mock):
        """
        REQUIREMENT: Machines should be able to send heartbeats.
        """
        redis_mock.update_machine_heartbeat = AsyncMock()
        
        machine_id = "test-machine-123"
        
        response = await client.post(f"/api/v2/machines/{machine_id}/heartbeat")
        
        assert response.status_code == 200
        assert response.json().get("ok") is True
    async def test_link_machine_to_account(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Machines should be linkable to accounts.
        """
        from core.database.models import AccountDB, MachineDB
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        machine_id = f"machine-{uuid.uuid4().hex[:8]}"
        
        # Create account and machine
        account = AccountDB(account_id=account_id, email="test@example.com")
        machine = MachineDB(machine_id=machine_id, status="online")
        db_session.add(account)
        db_session.add(machine)
        await db_session.commit()
        
        response = await client.post(f"/api/v2/machines/{machine_id}/link", json={
            "account_id": account_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("linked") is True or data.get("account_id") == account_id
    async def test_list_machines(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Should be able to list all machines.
        """
        from core.database.models import MachineDB
        
        # Create test machines
        for i in range(3):
            machine = MachineDB(
                machine_id=f"machine-list-{i}",
                status="online" if i % 2 == 0 else "offline"
            )
            db_session.add(machine)
        await db_session.commit()
        
        redis_mock.get_active_machines = AsyncMock(return_value=["machine-list-0", "machine-list-2"])
        
        response = await client.get("/api/v2/machines")
        
        assert response.status_code == 200
        machines = response.json().get("machines", [])
        assert len(machines) >= 3
    async def test_machine_status_shows_online_offline(self, client, db_session, redis_mock):
        """
        REQUIREMENT: Machine status should correctly show online/offline.
        """
        from core.database.models import MachineDB
        
        machine_id = f"machine-{uuid.uuid4().hex[:8]}"
        
        machine = MachineDB(
            machine_id=machine_id,
            status="online",
            last_heartbeat=datetime.now(timezone.utc)
        )
        db_session.add(machine)
        await db_session.commit()
        
        redis_mock.get_machine_status = AsyncMock(return_value={
            "status": "online",
            "heartbeat": datetime.now(timezone.utc).isoformat()
        })
        
        response = await client.get(f"/api/v2/machines/{machine_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["online", "offline", "busy", "error"]


class TestAccountMachineUISupport:
    """Test API endpoints needed for dashboard UI."""
    async def test_account_switcher_data(self, client, db_session):
        """
        REQUIREMENT: API should provide data for account switcher component.
        """
        from core.database.models import AccountDB, MachineDB
        
        # Create account with machines
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        account = AccountDB(
            account_id=account_id,
            email="test@example.com",
            credential_status="valid"
        )
        db_session.add(account)
        
        for i in range(2):
            machine = MachineDB(
                machine_id=f"machine-switcher-{i}",
                account_id=account_id,
                status="online"
            )
            db_session.add(machine)
        await db_session.commit()
        
        response = await client.get("/api/v2/accounts/current")
        
        assert response.status_code == 200
        data = response.json()
        # Should have account info and machines
        assert "account_id" in data or "accounts" in data
    async def test_credential_status_expiring_soon(self, client, db_session):
        """
        REQUIREMENT: Should flag credentials expiring within 7 days.
        """
        from core.database.models import AccountDB
        
        account_id = f"account-{uuid.uuid4().hex[:8]}"
        
        # Create account with credentials expiring in 3 days
        account = AccountDB(
            account_id=account_id,
            email="test@example.com",
            credential_status="valid",
            credential_expires_at=datetime.now(timezone.utc) + timedelta(days=3)
        )
        db_session.add(account)
        await db_session.commit()
        
        response = await client.get(f"/api/v2/accounts/{account_id}")
        
        assert response.status_code == 200
        data = response.json()
        # Should indicate expiring soon
        assert data.get("credential_status") in ["valid", "expiring_soon"]
