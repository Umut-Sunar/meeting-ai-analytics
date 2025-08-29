"""
Simplified WebSocket connection manager without control frame issues.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

MAX_TEXT_MESSAGE_SIZE = 64_000  # 64KB, safe for text frames


class ConnectionManager:
    """Simplified WebSocket manager."""
    
    def __init__(self):
        # meeting_id -> list of websockets
        self.subscriber_connections: Dict[str, List[WebSocket]] = {}
        # (meeting_id, source) -> websocket (one ingest per meeting+source combination)
        self.ingest_connections: Dict[Tuple[str, str], WebSocket] = {}
        # websocket -> (meeting_id, source) mapping for cleanup
        self.connection_meetings: Dict[WebSocket, Tuple[str, str]] = {}
    
    # Not used anymore - direct handling in ws.py endpoints
    # async def connect_subscriber(self, websocket: WebSocket, meeting_id: str) -> bool:
    # async def connect_ingest(self, websocket: WebSocket, meeting_id: str) -> bool:
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect websocket."""
        connection_info = self.connection_meetings.get(websocket)
        if not connection_info:
            return
            
        # Handle subscriber connections (still use meeting_id only)
        if isinstance(connection_info, str):
            # Legacy: connection_info is meeting_id for subscribers
            meeting_id = connection_info
            if meeting_id in self.subscriber_connections:
                if websocket in self.subscriber_connections[meeting_id]:
                    self.subscriber_connections[meeting_id].remove(websocket)
                    if not self.subscriber_connections[meeting_id]:
                        del self.subscriber_connections[meeting_id]
            logger.info(f"📤 Subscriber disconnected from meeting {meeting_id}")
        else:
            # New: connection_info is (meeting_id, source) tuple for ingest
            meeting_id, source = connection_info
            connection_key = (meeting_id, source)
            if connection_key in self.ingest_connections and self.ingest_connections[connection_key] == websocket:
                del self.ingest_connections[connection_key]
            logger.info(f"📤 Ingest disconnected from meeting {meeting_id} (source: {source})")
            
        # Clean up mapping
        if websocket in self.connection_meetings:
            del self.connection_meetings[websocket]
    

    
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

    async def send_to_ingest(self, meeting_id: str, source: str, message: dict) -> bool:
        """Send message to specific ingest connection using TEXT frame."""
        connection_key = (meeting_id, source)
        ws = self.ingest_connections.get(connection_key)
        if not ws:
            return False
            
        try:
            await ws.send_text(json.dumps(message, default=str))  # TEXT FRAME ✅
            return True
        except Exception as e:
            logger.warning(f"send_to_ingest failed for {meeting_id}:{source} - {e}")
            await self.disconnect(ws)
            return False

    async def send_error_and_close(self, websocket: WebSocket, code: str, message: str, close_code: int = 1002):
        """Send error and properly close connection."""
        payload = {"type": "error", "code": code, "message": message}
        try:
            # Yalnızca kabul edilmişse mesaj gönder
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(payload))
            # Her durumda close et
            await websocket.close(code=close_code, reason=message)
        except Exception as e:
            logger.error(f"send_error_and_close failed: {e}")
            try:
                await websocket.close()
            except:
                pass

    async def _send_status(self, websocket: WebSocket, meeting_id: str, status: str, message: str):
        """Send status as TEXT frame."""
        payload = {"type": "status", "meeting_id": meeting_id, "status": status, "message": message}
        try:
            # Sadece connected state'de send yap
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"send_status failed: {e}")

    def get_meeting_stats(self, meeting_id: str) -> dict:
        """Get meeting stats with dual-source support."""
        # Check for ingest connections by meeting_id
        mic_connected = (meeting_id, "mic") in self.ingest_connections
        sys_connected = (meeting_id, "sys") in self.ingest_connections
        
        return {
            "meeting_id": meeting_id,
            "subscriber_count": len(self.subscriber_connections.get(meeting_id, [])),
            "sources": {
                "mic": {"connected": mic_connected},
                "sys": {"connected": sys_connected}
            },
            "total_ingest_connections": len([k for k in self.ingest_connections.keys() if k[0] == meeting_id])
        }




# Global WebSocket manager instance
ws_manager = ConnectionManager()
