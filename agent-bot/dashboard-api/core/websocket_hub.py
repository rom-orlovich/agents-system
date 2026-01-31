"""WebSocket connection hub for real-time updates."""

from typing import Dict, Set
from fastapi import WebSocket
import structlog

from shared import WSMessage

logger = structlog.get_logger()


class WebSocketHub:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # session_id -> connections

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Register a WebSocket connection."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        logger.info("WebSocket connected", session_id=session_id)

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info("WebSocket disconnected", session_id=session_id)

    async def send_to_session(self, session_id: str, message: WSMessage) -> None:
        """Send message to all connections in a session."""
        connections = self._connections.get(session_id, set())
        dead_connections = set()

        for ws in connections:
            try:
                await ws.send_json(message.model_dump(mode="json"))
            except Exception as e:
                logger.warning(
                    "Failed to send to WebSocket", session_id=session_id, error=str(e)
                )
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self._connections[session_id].discard(ws)

    async def broadcast(self, message: WSMessage) -> None:
        """Broadcast message to all connections."""
        for session_id in list(self._connections.keys()):
            await self.send_to_session(session_id, message)

    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._connections)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())
