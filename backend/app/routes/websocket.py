"""
WebSocket routes for real-time communication.
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Any
from app.core.auth import get_current_user_ws
from app.api.base import BaseRouter
import logging
import json

logger = logging.getLogger(__name__)
router = BaseRouter(prefix="", tags=["websocket"])

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, form_id: str):
        await websocket.accept()
        if form_id not in self.active_connections:
            self.active_connections[form_id] = set()
        self.active_connections[form_id].add(websocket)
        logger.info(f"New WebSocket connection for form {form_id}")

    def disconnect(self, websocket: WebSocket, form_id: str):
        if form_id in self.active_connections:
            self.active_connections[form_id].remove(websocket)
            if not self.active_connections[form_id]:
                del self.active_connections[form_id]
        logger.info(f"WebSocket disconnected for form {form_id}")

    async def broadcast(self, form_id: str, message: dict):
        if form_id in self.active_connections:
            for connection in self.active_connections[form_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {str(e)}")

manager = ConnectionManager()

@router.websocket("/{form_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    form_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_ws)
):
    """WebSocket endpoint for real-time form updates."""
    try:
        await manager.connect(websocket, form_id)
        while True:
            try:
                data = await websocket.receive_json()
                # Process the received data
                # For now, just echo it back
                await manager.broadcast(form_id, data)
            except WebSocketDisconnect:
                manager.disconnect(websocket, form_id)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                await websocket.send_json({"error": str(e)})
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        if websocket.client_state.CONNECTED:
            await websocket.close() 