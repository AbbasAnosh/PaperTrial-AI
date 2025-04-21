from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Any
from app.core.auth import get_current_user_ws
from app.api.base import BaseRouter
import logging
import json

logger = logging.getLogger(__name__)
router = BaseRouter(prefix="/ws", tags=["websocket"])

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

async def websocket_endpoint(websocket: WebSocket, form_id: str, token: str = None):
    """WebSocket endpoint for real-time form updates"""
    try:
        # Authenticate user if token is provided
        if token:
            user = await get_current_user_ws(token)
            if not user:
                await websocket.close(code=1008)  # Policy Violation
                return

        await manager.connect(websocket, form_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await manager.broadcast(form_id, message)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    continue
        except WebSocketDisconnect:
            manager.disconnect(websocket, form_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, form_id)

# Register WebSocket route
router.add_api_route("/{form_id}", websocket_endpoint, methods=["GET"])

async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients"""
    # This function is now handled by the ConnectionManager class
    # Keeping it for backward compatibility
    logger.warning("broadcast_message is deprecated, use ConnectionManager.broadcast instead")
    pass 