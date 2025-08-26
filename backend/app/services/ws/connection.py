"""
Simplified WebSocket connection manager without control frame issues.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

MAX_TEXT_MESSAGE_SIZE = 64_000  # 64KB, safe for text frames


class ConnectionManager:
    """Simplified WebSocket manager."""
    
    def __init__(self):
        # meeting_id -> list of websockets
        self.subscriber_connections: Dict[str, List[WebSocket]] = {}
        # meeting_id -> websocket (only one ingest per meeting)
        self.ingest_connections: Dict[str, WebSocket] = {}
        # websocket -> meeting_id mapping for cleanup
        self.connection_meetings: Dict[WebSocket, str] = {}
    
    async def connect_subscriber(self, websocket: WebSocket, meeting_id: str) -> bool:
        """Connect subscriber with simple boolean return."""
        current = len(self.subscriber_connections.get(meeting_id, []))
        if current >= settings.MAX_WS_CLIENTS_PER_MEETING:
            await self._send_error(websocket, "connection_limit", f"Max {settings.MAX_WS_CLIENTS_PER_MEETING}")
            return False
            
        await websocket.accept()
        self.subscriber_connections.setdefault(meeting_id, []).append(websocket)
        self.connection_meetings[websocket] = meeting_id
        
        logger.info(f"📥 Subscriber connected to meeting {meeting_id}")
        await self._send_status(websocket, meeting_id, "connected", "WS connected")
        return True
    
    async def connect_ingest(self, websocket: WebSocket, meeting_id: str) -> bool:
        """Connect ingest with simple boolean return."""
        if meeting_id in self.ingest_connections:
            await self._send_error(websocket, "ingest_exists", "Ingest already active")
            return False
            
        await websocket.accept()
        self.ingest_connections[meeting_id] = websocket
        self.connection_meetings[websocket] = meeting_id
        
        logger.info(f"🎤 Ingest connected to meeting {meeting_id}")
        await self._send_status(websocket, meeting_id, "connected", "Ingest connected")
        return True
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect websocket."""
        meeting_id = self.connection_meetings.get(websocket)
        if not meeting_id:
            return
            
        # Remove from subscribers
        if meeting_id in self.subscriber_connections:
            if websocket in self.subscriber_connections[meeting_id]:
                self.subscriber_connections[meeting_id].remove(websocket)
                if not self.subscriber_connections[meeting_id]:
                    del self.subscriber_connections[meeting_id]
                    
        # Remove from ingest
        if meeting_id in self.ingest_connections and self.ingest_connections[meeting_id] == websocket:
            del self.ingest_connections[meeting_id]
            
        # Clean up mapping
        if websocket in self.connection_meetings:
            del self.connection_meetings[websocket]
            
        logger.info(f"📤 Disconnected from meeting {meeting_id}")
    

    
    async def broadcast_to_meeting(self, meeting_id: str, message: dict):
        """Broadcast message using TEXT frames only."""
        conns = self.subscriber_connections.get(meeting_id, [])
        if not conns:
            return
            
        message_str = json.dumps(message, default=str)
        if len(message_str) > MAX_TEXT_MESSAGE_SIZE:
            # Truncate if too large
            message_str = json.dumps({
                "type": message.get("type", "status"),
                "meeting_id": meeting_id,
                "status": "truncated", 
                "message": "payload too large"
            })
            
        dead = []
        for ws in conns:
            try:
                await ws.send_text(message_str)  # TEXT FRAME ✅
            except Exception as e:
                logger.warning(f"broadcast failed: {e}")
                dead.append(ws)
                
        # Clean up dead connections
        for ws in dead:
            await self.disconnect(ws)

    async def send_to_ingest(self, meeting_id: str, message: dict) -> bool:
        """Send message to ingest using TEXT frame."""
        ws = self.ingest_connections.get(meeting_id)
        if not ws:
            return False
            
        try:
            await ws.send_text(json.dumps(message, default=str))  # TEXT FRAME ✅
            return True
        except Exception as e:
            logger.warning(f"send_to_ingest failed: {e}")
            await self.disconnect(ws)
            return False

    async def _send_error(self, websocket: WebSocket, code: str, message: str):
        """Send error as TEXT frame."""
        payload = {"type": "error", "code": code, "message": message}
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"send_error failed: {e}")

    async def _send_status(self, websocket: WebSocket, meeting_id: str, status: str, message: str):
        """Send status as TEXT frame."""
        payload = {"type": "status", "meeting_id": meeting_id, "status": status, "message": message}
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"send_status failed: {e}")

    def get_meeting_stats(self, meeting_id: str) -> dict:
        """Get meeting stats."""
        return {
            "meeting_id": meeting_id,
            "subscriber_count": len(self.subscriber_connections.get(meeting_id, [])),
            "has_ingest": meeting_id in self.ingest_connections
        }




# Global WebSocket manager instance
ws_manager = ConnectionManager()
