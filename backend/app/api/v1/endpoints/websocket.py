"""
WebSocket endpoints for real-time workflow monitoring
"""
import asyncio
import json
import logging
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from app.core.websocket_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str,
    user_id: Optional[str] = Query(default="anonymous"),
):
    """
    WebSocket endpoint for real-time workflow monitoring.
    
    Connect with: ws://localhost:8000/ws/{workflow_id}
    
    Events received:
    - workflow_started: Workflow execution begins
    - stage_started: A new agent stage begins
    - agent_event: Individual agent status updates
    - log: Execution log entries
    - security_event: Security alerts
    - workflow_completed: Final results
    """
    await ws_manager.connect(websocket, user_id=user_id, workflow_id=workflow_id)
    logger.info(f"WebSocket connected: workflow={workflow_id}, user={user_id}")
    
    try:
        # Keep connection alive with ping/pong
        while True:
            try:
                # Wait for client messages (ping or commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30s timeout, then send heartbeat
                )
                
                try:
                    message = json.loads(data)
                    await _handle_client_message(websocket, workflow_id, message)
                except json.JSONDecodeError:
                    pass
            
            except asyncio.TimeoutError:
                # Send heartbeat ping
                try:
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": time.time(),
                    }))
                except Exception:
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: workflow={workflow_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/system/events")
async def system_events_websocket(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default="anonymous"),
):
    """
    WebSocket for global system events (security, health, observability).
    Not tied to a specific workflow.
    """
    await ws_manager.connect(websocket, user_id=user_id, workflow_id="system")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat",
                        "connections": ws_manager.connection_count,
                        "timestamp": time.time(),
                    }))
                except Exception:
                    break
    
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


async def _handle_client_message(websocket: WebSocket, workflow_id: str, message: dict):
    """Handle messages from WebSocket clients."""
    msg_type = message.get("type")
    
    if msg_type == "pong":
        # Heartbeat response
        pass
    
    elif msg_type == "subscribe":
        # Subscribe to additional workflow
        pass
    
    elif msg_type == "get_status":
        from app.agents.orchestrator import orchestrator
        status = orchestrator.get_workflow_status(workflow_id)
        await websocket.send_text(json.dumps({
            "type": "status_response",
            "workflow_id": workflow_id,
            "status": status,
            "timestamp": time.time(),
        }))
