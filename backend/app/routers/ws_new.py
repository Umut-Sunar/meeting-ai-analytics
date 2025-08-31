"""
WebSocket endpoints for real-time communication.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.core.security import decode_jwt_token, SecurityError
from app.core.config import get_settings
from app.services.ws.connection import ws_manager
from app.services.pubsub.redis_bus import redis_bus
from app.services.ws.messages import (
    TranscriptMessage, 
    TranscriptSegment,
    WebSocketMessage,
    MessageType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Meeting segments storage for transcript accumulation
meeting_segments: Dict[str, list] = {}


async def send_error_and_close(ws: WebSocket, code: int, message: str, error_type: str = "error"):
    """Send error message and close WebSocket connection."""
    try:
        error_msg = {
            "type": error_type,
            "message": message,
            "code": code
        }
        await ws.send_json(error_msg)
        await ws.close(code=code, reason=message)
    except Exception as e:
        logger.warning(f"Error sending error message: {e}")
        try:
            await ws.close(code=code, reason=message)
        except Exception:
            pass


@router.websocket("/ws/meetings/{meeting_id}")
async def websocket_subscriber(websocket: WebSocket, meeting_id: str, token: str = Query(...)):
    """
    WebSocket endpoint for subscribing to meeting transcripts.
    Clients connect here to receive real-time transcript updates.
    """
    try:
        # Validate JWT token
        try:
            claims = decode_jwt_token(token)
            logger.info(f"[WS][SUB] Auth success: {claims.email} for meeting {meeting_id}")
        except SecurityError as e:
            logger.warning(f"[WS][SUB] Auth failed for meeting {meeting_id}: {e}")
            await send_error_and_close(websocket, 1008, f"Authentication failed: {e}")
            return

        # Accept connection
        await websocket.accept()
        await ws_manager.connect(websocket, meeting_id)
        
        logger.info(f"[WS][SUB] Client connected to meeting {meeting_id}")
        
        # Keep connection alive and handle client messages
        try:
            while True:
                # Wait for client messages (ping, etc.)
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    # Handle client messages if needed (ping/pong, etc.)
                    logger.debug(f"[WS][SUB] Received message from client: {message}")
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await websocket.send_json({"type": "ping"})
                    continue
                    
        except WebSocketDisconnect:
            logger.info(f"[WS][SUB] Client disconnected from meeting {meeting_id}")
        except Exception as e:
            logger.error(f"[WS][SUB] Error in subscriber loop: {e}")
            
    except Exception as e:
        logger.error(f"[WS][SUB] Unexpected error: {e}")
        try:
            await send_error_and_close(websocket, 1011, "Internal server error")
        except Exception:
            pass
    finally:
        # Cleanup
        try:
            await ws_manager.disconnect(websocket)
            logger.info(f"[WS][SUB] Cleanup completed for meeting {meeting_id}")
        except Exception as e:
            logger.warning(f"[WS][SUB] Cleanup error: {e}")


# Global registry for ingest connections - keyed by (meeting_id, source)
ingest_registry: Dict[Tuple[str, str], Dict[str, Any]] = {}

@router.websocket("/ws/ingest/meetings/{meeting_id}")
async def websocket_ingest(websocket: WebSocket, meeting_id: str, source: str = Query("mic", regex="^(mic|sys|system)$"), token: str = Query(None)):
    """WebSocket ingest endpoint with rate limiting, handshake protocol and structured logging."""
    # Delegate to the new structured ingest handler
    from app.websocket.ingest import handle_websocket_ingest
    await handle_websocket_ingest(websocket, meeting_id, source, token)


@router.websocket("/transcript/{meeting_id}")
async def websocket_transcript(websocket: WebSocket, meeting_id: str):
    """
    Frontend WebSocket endpoint for receiving real-time transcripts.
    Subscribes to Redis transcript messages and forwards to frontend.
    """
    try:
        await websocket.accept()
        logger.info(f"🌐 Frontend WebSocket connected for meeting: {meeting_id}")
        
        # Subscribe to Redis transcript channel
        transcript_channel = f"transcript:{meeting_id}"
        
        async def transcript_handler(message):
            """Handle incoming transcript messages from Redis."""
            try:
                if isinstance(message, dict):
                    transcript_data = message
                else:
                    transcript_data = json.loads(message)
                
                # Forward to frontend
                await websocket.send_json(transcript_data)
                logger.debug(f"🌐 Forwarded transcript to frontend: {meeting_id}")
                
            except Exception as e:
                logger.error(f"🌐 Error handling transcript message: {e}")
        
        # Subscribe to Redis channel
        await redis_bus.subscribe(transcript_channel, transcript_handler)
        logger.info(f"🌐 Subscribed to Redis channel: {transcript_channel}")
        
        # Keep connection alive
        try:
            while True:
                try:
                    # Wait for client messages (ping, etc.)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    logger.debug(f"🌐 Received message from frontend: {message}")
                    
                    # Handle ping/pong
                    if message == "ping":
                        await websocket.send_text("pong")
                        
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                    continue
                    
        except WebSocketDisconnect:
            logger.info(f"🌐 Frontend WebSocket disconnected for meeting: {meeting_id}")
        except Exception as e:
            logger.error(f"🌐 Error in frontend WebSocket loop: {e}")
            
    except Exception as e:
        logger.error(f"🌐 Unexpected error in frontend WebSocket: {e}")
    finally:
        # Cleanup
        try:
            await redis_bus.unsubscribe(transcript_channel)
            logger.info(f"🌐 Unsubscribed from Redis channel: {transcript_channel}")
        except Exception as e:
            logger.warning(f"🌐 Error unsubscribing from Redis: {e}")
        
        logger.info(f"🌐 Frontend WebSocket cleanup completed for meeting: {meeting_id}")


@router.get("/ws/meetings/{meeting_id}/stats")
async def get_meeting_stats(meeting_id: str):
    """Get WebSocket connection statistics for a meeting."""
    return ws_manager.get_meeting_stats(meeting_id)
