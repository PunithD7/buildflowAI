"""
Agents status and management endpoints
"""
from fastapi import APIRouter
from app.agents.agents import AGENT_REGISTRY
from app.agents.orchestrator import orchestrator

router = APIRouter()


@router.get("")
async def list_agents():
    """List all available agents with their status."""
    agents = []
    for key, agent_class in AGENT_REGISTRY.items():
        agent_instance = agent_class()
        agents.append({
            "key": key,
            "name": agent_instance.name,
            "description": agent_instance.description,
            "max_retries": agent_instance.max_retries,
            "timeout_seconds": agent_instance.timeout_seconds,
            "can_fail_over": agent_instance.can_fail_over,
            "status": "ready",
        })
    return {"agents": agents, "total": len(agents)}


@router.get("/active")
async def get_active_agents():
    """Get currently active agents across all workflows."""
    active_workflows = orchestrator.get_active_workflows()
    return {
        "active_workflows": active_workflows,
        "active_workflow_count": len(active_workflows),
    }
