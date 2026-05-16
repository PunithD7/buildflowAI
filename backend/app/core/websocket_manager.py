"""
WebSocket Manager - Real-time event broadcasting

FIXES APPLIED:
  - Added event replay buffer per workflow_id (last 200 events stored in memory).
    When a WebSocket client connects to a workflow room, all buffered events are
    replayed immediately so the client doesn't miss workflow_started, stage_started,
    or agent events that fired before the connection was established.
  - Added detailed logging for every emit so WS activity is visible in backend logs.
"""
import asyncio
import json
import logging
import time
from collections import deque
from typing import Any, Deque, Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Maximum number of events to buffer per workflow (in memory)
_REPLAY_BUFFER_SIZE = 200


class ConnectionManager:
    """Manages WebSocket connections with room/channel support and event replay."""

    def __init__(self):
        # All active connections: ws -> metadata
        self._connections: Dict[WebSocket, Dict[str, Any]] = {}
        # Room-based connections: room_id -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # Event replay buffer: workflow_id -> deque of events (most recent last)
        self._replay_buffers: Dict[str, Deque[Dict]] = {}
        # Lock for thread safety
        self._lock = asyncio.Lock()

    def _get_or_create_buffer(self, workflow_id: str) -> Deque[Dict]:
        """Get or create a replay buffer for a workflow."""
        if workflow_id not in self._replay_buffers:
            self._replay_buffers[workflow_id] = deque(maxlen=_REPLAY_BUFFER_SIZE)
        return self._replay_buffers[workflow_id]

    def _buffer_event(self, workflow_id: str, data: Dict):
        """Store an event in the workflow replay buffer."""
        buf = self._get_or_create_buffer(workflow_id)
        buf.append(data)
        logger.debug(
            f"[WSManager] Buffered event | workflow={workflow_id[:8]} "
            f"type={data.get('type', 'unknown')} buffer_size={len(buf)}"
        )

    async def connect(self, websocket: WebSocket, user_id: str = None, workflow_id: str = None):
        """
        Accept and register a WebSocket connection.
        If connecting to a workflow room, replay all buffered events immediately.
        """
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = {
                "user_id": user_id,
                "workflow_id": workflow_id,
                "connected_at": time.time(),
                "last_ping": time.time(),
            }
            if workflow_id:
                if workflow_id not in self._rooms:
                    self._rooms[workflow_id] = set()
                self._rooms[workflow_id].add(websocket)

        logger.info(
            f"[WSManager] ✅ Client connected | user={user_id} workflow={workflow_id} "
            f"total_connections={len(self._connections)} rooms={len(self._rooms)}"
        )

        # Send welcome message
        await self._send_to_socket(websocket, {
            "type": "connected",
            "message": "Connected to BuildFlow Secure AI",
            "timestamp": time.time(),
        })

        # FIX: Replay buffered events so client doesn't miss workflow_started,
        # stage_started, or early agent events that fired before WS connected.
        if workflow_id and workflow_id in self._replay_buffers:
            buffered = list(self._replay_buffers[workflow_id])
            if buffered:
                logger.info(
                    f"[WSManager] 🔄 Replaying {len(buffered)} buffered events "
                    f"for workflow={workflow_id[:8]}"
                )
                # Send replay marker so UI can distinguish replayed vs live
                await self._send_to_socket(websocket, {
                    "type": "replay_start",
                    "event_count": len(buffered),
                    "workflow_id": workflow_id,
                    "timestamp": time.time(),
                })
                for event in buffered:
                    await self._send_to_socket(websocket, {**event, "replayed": True})
                await self._send_to_socket(websocket, {
                    "type": "replay_end",
                    "workflow_id": workflow_id,
                    "timestamp": time.time(),
                })
                logger.info(f"[WSManager] ✅ Replay complete for workflow={workflow_id[:8]}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            meta = self._connections.pop(websocket, {})
            workflow_id = meta.get("workflow_id")
            if workflow_id and workflow_id in self._rooms:
                self._rooms[workflow_id].discard(websocket)
                if not self._rooms[workflow_id]:
                    del self._rooms[workflow_id]

        logger.debug(
            f"[WSManager] Client disconnected | total_connections={len(self._connections)}"
        )

    async def _send_to_socket(self, websocket: WebSocket, data: Dict) -> bool:
        """Send data to a single WebSocket, handling errors."""
        try:
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.debug(f"[WSManager] Send error (client disconnected): {e}")
            await self.disconnect(websocket)
            return False

    async def send_to_workflow(self, workflow_id: str, data: Dict):
        """
        Broadcast message to all connections in a workflow room.
        Also buffers the event for clients that connect later (replay buffer).
        """
        # Always buffer the event first (for replay)
        self._buffer_event(workflow_id, data)

        sockets = list(self._rooms.get(workflow_id, set()))

        if not sockets:
            logger.debug(
                f"[WSManager] No live clients for workflow={workflow_id[:8]} "
                f"| type={data.get('type')} (buffered for replay)"
            )
            return

        logger.debug(
            f"[WSManager] 📤 Emitting to {len(sockets)} client(s) | "
            f"workflow={workflow_id[:8]} type={data.get('type')}"
        )

        tasks = [self._send_to_socket(ws, data) for ws in sockets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        sent = sum(1 for r in results if r is True)
        logger.debug(f"[WSManager] Emit done | sent={sent}/{len(sockets)}")

    async def broadcast_system_event(self, data: Dict):
        """Broadcast to ALL connected clients."""
        sockets = list(self._connections.keys())
        if not sockets:
            return

        logger.debug(f"[WSManager] 📢 Broadcasting system event | type={data.get('type')} clients={len(sockets)}")
        tasks = [self._send_to_socket(ws, data) for ws in sockets]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_agent_event(
        self, workflow_id: str, agent_name: str, event_type: str, payload: Dict
    ):
        """Send agent execution event."""
        event = {
            "type": "agent_event",
            "event": event_type,
            "agent": agent_name,
            "workflow_id": workflow_id,
            "payload": payload,
            "timestamp": time.time(),
        }
        logger.info(
            f"[WSManager] 🤖 Agent event | agent={agent_name} "
            f"event={event_type} workflow={workflow_id[:8]}"
        )
        await self.send_to_workflow(workflow_id, event)

    async def send_log_entry(
        self, workflow_id: str, level: str, message: str, source: str = None
    ):
        """Send a log entry to workflow subscribers."""
        event = {
            "type": "log",
            "level": level,
            "message": message,
            "source": source,
            "workflow_id": workflow_id,
            "timestamp": time.time(),
        }
        logger.debug(f"[WSManager] 📋 Log | level={level} workflow={workflow_id[:8]} msg={message[:80]}")
        await self.send_to_workflow(workflow_id, event)

    async def send_security_event(self, event_type: str, details: Dict):
        """Broadcast security event to all clients."""
        await self.broadcast_system_event({
            "type": "security_event",
            "event": event_type,
            "details": details,
            "timestamp": time.time(),
        })

    def clear_workflow_buffer(self, workflow_id: str):
        """Clear the replay buffer for a completed workflow (memory cleanup)."""
        if workflow_id in self._replay_buffers:
            del self._replay_buffers[workflow_id]
            logger.debug(f"[WSManager] Cleared replay buffer for workflow={workflow_id[:8]}")

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    @property
    def room_count(self) -> int:
        return len(self._rooms)


# Singleton
ws_manager = ConnectionManager()
