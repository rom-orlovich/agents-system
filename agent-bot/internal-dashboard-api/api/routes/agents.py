from fastapi import APIRouter

from services import AgentManager

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
agent_manager = AgentManager()


@router.get("")
async def list_agents():
    return await agent_manager.list_agents()


@router.get("/status")
async def get_agents_status():
    return await agent_manager.get_agent_status()


@router.get("/health")
async def get_agents_health():
    return await agent_manager.get_agent_health()


@router.get("/metrics")
async def get_agents_metrics():
    return await agent_manager.get_agent_metrics()
