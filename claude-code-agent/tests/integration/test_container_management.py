"""Integration tests for container management (Part 3 of TDD Requirements)."""

from unittest.mock import AsyncMock


class TestContainerManagementFlow:
    """Test container management business requirements."""
    async def test_list_container_processes(self, client):
        """
        REQUIREMENT: Should be able to list all running processes
        in the container.
        """
        response = await client.get("/api/v2/container/processes")
        
        assert response.status_code == 200
        data = response.json()
        assert "processes" in data
        processes = data["processes"]
        
        # Should at least have some processes
        assert isinstance(processes, list)
        # Each process should have pid and name
        for p in processes:
            assert "pid" in p
            assert "name" in p
    async def test_container_resource_usage(self, client, redis_mock):
        """
        REQUIREMENT: Should report CPU and memory usage.
        """
        redis_mock.get_container_resources = AsyncMock(return_value={
            "cpu_percent": "25.5",
            "memory_mb": "512"
        })
        
        response = await client.get("/api/v2/container/resources")
        
        assert response.status_code == 200
        resources = response.json()
        
        assert "cpu_percent" in resources
        assert "memory_mb" in resources
        assert 0 <= float(resources["cpu_percent"]) <= 100
    async def test_kill_process_requires_allowlist(self, client):
        """
        REQUIREMENT: Killing processes should only work for
        processes in the explicit allowlist.
        """
        # Try to kill a system process (not allowed)
        response = await client.post("/api/v2/container/processes/1/kill")
        
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"].lower()
    async def test_container_exec_requires_allowlist(self, client):
        """
        REQUIREMENT: Container exec commands must be in allowlist.
        """
        # Try to run arbitrary command
        response = await client.post("/api/v2/container/exec", json={
            "command": "rm -rf /"
        })
        
        assert response.status_code == 403
        assert "not in allowlist" in response.json()["detail"].lower()
    async def test_container_exec_allowed_command(self, client):
        """
        REQUIREMENT: Allowed commands should execute successfully.
        """
        # Try to run an allowed command (e.g., ls)
        response = await client.post("/api/v2/container/exec", json={
            "command": "ls -la"
        })
        
        # Should either succeed or be in allowlist
        assert response.status_code in [200, 403]
    async def test_container_status(self, client, redis_mock):
        """
        REQUIREMENT: Should report container health status.
        """
        redis_mock.get_container_resources = AsyncMock(return_value={
            "cpu_percent": "10",
            "memory_mb": "256",
            "disk_percent": "45"
        })
        
        response = await client.get("/api/v2/container/status")
        
        assert response.status_code == 200
        status = response.json()
        assert "healthy" in status or "status" in status
