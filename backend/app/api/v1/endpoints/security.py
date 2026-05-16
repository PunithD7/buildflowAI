"""
Security endpoints - Rate limits, DDoS, TEE management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.middleware.ddos_protection import ddos_tracker
from app.core.websocket_manager import ws_manager

router = APIRouter()


class SimulateDDoSRequest(BaseModel):
    attacker_ip: str = "192.168.100.1"
    requests: int = 200


@router.get("/ddos/stats")
async def get_ddos_stats():
    """Get DDoS protection statistics."""
    return ddos_tracker.get_stats()


@router.post("/ddos/simulate")
async def simulate_ddos_attack(request: SimulateDDoSRequest):
    """
    Simulate a DDoS attack for demonstration purposes.
    This is for observability demo only - it bans the fake attacker IP.
    """
    result = ddos_tracker.simulate_attack(
        attacker_ip=request.attacker_ip,
        requests=request.requests,
    )
    
    # Broadcast security event
    await ws_manager.send_security_event("ddos_simulation", {
        "attacker_ip": request.attacker_ip,
        "requests": request.requests,
        "result": "ip_banned",
    })
    
    return {
        "simulation": result,
        "message": "DDoS simulation complete. IP has been banned.",
        "alert_broadcast": "Security event sent to all connected clients.",
    }


@router.post("/ddos/unban/{ip}")
async def unban_ip(ip: str):
    """Unban an IP address (admin action)."""
    unbanned = ddos_tracker.unban_ip(ip)
    if not unbanned:
        raise HTTPException(status_code=404, detail=f"IP {ip} was not banned")
    return {"message": f"IP {ip} has been unbanned", "status": "success"}


@router.get("/rate-limits/status")
async def get_rate_limit_status():
    """Get current rate limiting status."""
    from app.core.config import settings
    return {
        "rate_limiting": "active",
        "limits": {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.RATE_LIMIT_PER_HOUR,
            "burst": settings.RATE_LIMIT_BURST,
            "agent_per_minute": settings.AGENT_RATE_LIMIT_PER_MINUTE,
            "token_budget_per_request": settings.TOKEN_BUDGET_PER_REQUEST,
        },
        "protection_features": [
            "Per-user rate limits",
            "Progressive blocking with escalating cooldowns",
            "Burst protection",
            "Token budget management",
            "Abuse pattern detection",
        ]
    }


@router.get("/tee/status")
async def get_tee_status():
    """Get TEE-inspired execution environment status."""
    return {
        "tee_execution": "active",
        "features": {
            "isolated_execution": True,
            "sandboxed_agent_tasks": True,
            "encrypted_secret_storage": True,
            "temporary_execution_memory": True,
            "restricted_permissions": True,
        },
        "active_sandboxes": 0,
        "note": "TEE-inspired isolation (software-level, not hardware TEE)"
    }
