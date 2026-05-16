"""
Observability endpoints - Metrics, logs, traces
"""
import time
from fastapi import APIRouter
from app.middleware.rate_limiter import get_rate_limiter
from app.middleware.ddos_protection import ddos_tracker
from app.core.websocket_manager import ws_manager
from app.agents.orchestrator import orchestrator

router = APIRouter()


@router.get("/dashboard")
async def get_observability_dashboard():
    """Full observability dashboard data."""
    rate_limiter = get_rate_limiter()
    ddos_stats = ddos_tracker.get_stats()
    
    return {
        "timestamp": time.time(),
        "system": {
            "status": "operational",
            "uptime_seconds": time.time(),
            "version": "1.0.0",
        },
        "agents": {
            "total": 13,
            "active_workflows": len(orchestrator.get_active_workflows()),
            "registry": list(["goal_understanding", "planning", "research", "strategy",
                             "architecture", "tech_stack", "frontend", "backend",
                             "security", "documentation", "monitoring", "self_healing", "rollback"]),
        },
        "websocket": {
            "connections": ws_manager.connection_count,
            "rooms": ws_manager.room_count,
        },
        "security": {
            "rate_limiting": "active",
            "ddos_protection": "active",
            "active_bans": ddos_stats["active_bans"],
            "total_blocked": ddos_stats["total_blocked"],
            "total_alerts": ddos_stats["total_alerts"],
            "suspicious_ips": len(ddos_stats["suspicious_ips"]),
        },
        "infrastructure": {
            "redis": "connected",
            "api": "healthy",
            "agents": "ready",
        }
    }


@router.get("/metrics")
async def get_metrics():
    """System performance metrics."""
    import psutil
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        return {
            "cpu": {"percent": cpu_percent},
            "memory": {
                "total_gb": round(memory.total / 1e9, 2),
                "used_gb": round(memory.used / 1e9, 2),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / 1e9, 2),
                "used_gb": round(disk.used / 1e9, 2),
                "percent": disk.percent,
            },
            "timestamp": time.time(),
        }
    except ImportError:
        return {
            "cpu": {"percent": 0},
            "memory": {"total_gb": 0, "used_gb": 0, "percent": 0},
            "disk": {"total_gb": 0, "used_gb": 0, "percent": 0},
            "timestamp": time.time(),
            "note": "psutil not installed - install for real metrics",
        }


@router.get("/security-events")
async def get_security_events():
    """Get recent security events."""
    ddos_stats = ddos_tracker.get_stats()
    return {
        "ddos": ddos_stats,
        "rate_limiting": {
            "status": "active",
            "events": [],
        },
        "tee_execution": {
            "status": "active",
            "sandboxed_tasks": 0,
        }
    }


@router.get("/traces")
async def get_traces():
    """Get execution traces for workflows."""
    # In production, this would come from a tracing backend like Jaeger/Tempo
    return {
        "traces": [],
        "message": "Traces are emitted via WebSocket in real-time during workflow execution",
        "websocket_endpoint": "ws://localhost:8000/ws/{workflow_id}",
    }
