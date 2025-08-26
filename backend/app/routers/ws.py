"""
Simplified WebSocket endpoints.
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.security import decode_jwt_token, SecurityError
from app.services.ws.connection import ws_manager
from app.services.ws.messages import (
    IngestHandshakeMessage, IngestControlMessage, 
    create_transcript_message, create_status_message, create_error_message
)
from app.services.asr.deepgram_live import DeepgramLiveClient
from app.services.transcript.store import transcript_store
from app.services.pubsub.redis_bus import redis_bus
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Global segment counter
meeting_segments = {}


@router.websocket("/ws/meetings/{meeting_id}")
async def websocket_subscriber(websocket: WebSocket, meeting_id: str, token: str = Query(...)):
    """Simplified subscriber endpoint."""
    try:
        # Auth
        try:
            claims = decode_jwt_token(token)
            logger.info(f"Subscriber auth: {claims.email}")
        except SecurityError as e:
            await websocket.close(code=4001, reason=f"auth failed: {e}")
            return
            
        # Connect
        if not await ws_manager.connect_subscriber(websocket, meeting_id):
            return

        # Subscribe to Redis
        transcript_topic = redis_bus.get_meeting_transcript_topic(meeting_id)

        async def handle_redis_message(channel: str, message: dict):
            await ws_manager.broadcast_to_meeting(meeting_id, message)

        await redis_bus.subscribe(transcript_topic, handle_redis_message)
        logger.info(f"Subscribed to {transcript_topic}")

        # Keep-alive loop with TEXT ping/pong
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    if msg == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    await websocket.send_text("ping")
                    
        except WebSocketDisconnect:
            logger.info(f"Subscriber disconnected from {meeting_id}")
        except Exception as e:
            logger.error(f"Subscriber error: {e}")
            
    finally:
        await ws_manager.disconnect(websocket)
        try:
            await redis_bus.unsubscribe(transcript_topic)
        except Exception:
            pass


@router.websocket("/ws/ingest/meetings/{meeting_id}")
async def websocket_ingest(websocket: WebSocket, meeting_id: str, token: str = Query(...)):
    """Simplified ingest endpoint."""
    client: Optional[DeepgramLiveClient] = None
    
    try:
        # Auth
        try:
            claims = decode_jwt_token(token)
            logger.info(f"Ingest auth: {claims.email}")
        except SecurityError as e:
            await websocket.close(code=4001, reason=f"auth failed: {e}")
            return

        # Connect
        if not await ws_manager.connect_ingest(websocket, meeting_id):
            return

        # Handshake
        try:
            hs_data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            hs = IngestHandshakeMessage.model_validate_json(hs_data)
            logger.info(f"Handshake: {hs}")
        except Exception as e:
            await websocket.send_text(json.dumps({"status": "error", "message": f"Handshake invalid: {e}"}))
            return

        # Validate handshake
        if hs.sample_rate != settings.INGEST_SAMPLE_RATE:
            await websocket.send_text(json.dumps({"status": "error", "message": f"Invalid sample rate {hs.sample_rate}"}))
            return
        if hs.channels != settings.INGEST_CHANNELS:
            await websocket.send_text(json.dumps({"status": "error", "message": f"Invalid channels {hs.channels}"}))
            return

        # Initialize segment counter
        if meeting_id not in meeting_segments:
            meeting_segments[meeting_id] = 0

        # Deepgram callbacks
        async def on_transcript(res: dict):
            is_final = res.get("is_final", False)
            
            if is_final:
                meeting_segments[meeting_id] += 1
                
            msg = create_transcript_message(
                meeting_id=meeting_id, 
                segment_no=meeting_segments[meeting_id] if is_final else meeting_segments.get(meeting_id, 0),
                text=res["text"], start_ms=res["start_ms"], end_ms=res["end_ms"], 
                is_final=is_final, speaker=res.get("speaker"),
                confidence=res.get("confidence"), source=hs.source
            )
            
            # Store in database if final
            if is_final:
                await transcript_store.store_final_transcript(
                    meeting_id=meeting_id, segment_no=meeting_segments[meeting_id], text=res["text"],
                    start_ms=res["start_ms"], end_ms=res["end_ms"], speaker=res.get("speaker"),
                    confidence=res.get("confidence"), raw_json=res.get("raw_result")
                )
            
            # Publish to Redis
            await redis_bus.publish(redis_bus.get_meeting_transcript_topic(meeting_id), msg.model_dump())

        async def on_err(err: str):
            logger.error(f"Deepgram error: {err}")
            await ws_manager.send_to_ingest(meeting_id, {"type": "error", "code": "deepgram_error", "message": err})

        # Create Deepgram client
        client = DeepgramLiveClient(
            meeting_id=meeting_id, language=hs.language, sample_rate=hs.sample_rate,
            on_transcript=on_transcript, on_error=on_err
        )
        
        try:
            await client.connect()
            logger.info(f"Connected to Deepgram for {meeting_id}")
        except Exception as e:
            await websocket.send_text(json.dumps({"status": "error", "message": f"Deepgram connect failed: {e}"}))
            return

        # Send success response
        await websocket.send_text(json.dumps({"status": "success", "message": "Connected to transcription", "session_id": f"sess-{meeting_id}"}))

        # Process messages
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message and message["bytes"] is not None:
                    # Audio data
                    data = message["bytes"]
                    if len(data) > settings.MAX_INGEST_MSG_BYTES:
                        logger.warning(f"Frame too large: {len(data)}")
                        continue
                    await client.send_pcm(data)  # ✅ Correct method name
                    
                elif "text" in message and message["text"] is not None:
                    # Control message
                    try:
                        ctrl = IngestControlMessage.model_validate_json(message["text"])
                        if ctrl.type == "finalize":
                            logger.info(f"Finalizing {meeting_id}")
                            await client.finalize()
                            break
                        if ctrl.type == "close":
                            break
                    except Exception as e:
                        logger.warning(f"Invalid control: {e}")
                        
            elif message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        logger.info(f"Ingest disconnected from {meeting_id}")
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        await ws_manager.disconnect(websocket)
        meeting_segments.pop(meeting_id, None)


@router.get("/ws/meetings/{meeting_id}/stats")
async def get_meeting_stats(meeting_id: str):
    """Get meeting stats."""
    return ws_manager.get_meeting_stats(meeting_id)
