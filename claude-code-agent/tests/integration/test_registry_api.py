"""Integration tests for registry API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistryAPI:
    """Integration tests for registry endpoints."""
    
    async def test_list_skills(self, client: AsyncClient):
        """List skills returns list."""
        response = await client.get("/api/registry/skills")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_upload_skill_without_skill_md(self, client: AsyncClient):
        """Upload skill without SKILL.md is rejected."""
        response = await client.post(
            "/api/registry/skills/upload",
            data={"name": "test-skill"},
            files=[
                ("files", ("readme.txt", b"test", "text/plain")),
            ]
        )
        
        assert response.status_code == 400
        assert "SKILL.md is required" in response.json()["detail"]
    
    async def test_delete_nonexistent_skill(self, client: AsyncClient):
        """Delete nonexistent skill returns 404."""
        response = await client.delete("/api/registry/skills/nonexistent-skill-xyz")
        assert response.status_code == 404
    
    async def test_list_agents(self, client: AsyncClient):
        """List agents returns agent list."""
        response = await client.get("/api/registry/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
