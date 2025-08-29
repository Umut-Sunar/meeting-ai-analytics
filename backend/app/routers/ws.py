"""
Simplified WebSocket endpoints.
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketState

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

# Frontend WebSocket connections for transcript streaming
frontend_connections = {}


async def send_error_and_close(ws: WebSocket, code: int, message: str, error_type: str = "error"):
    """Send error message and close WebSocket safely, respecting ASGI protocol."""
    try:
        # Only send if WebSocket is connected (already accepted)
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps({
                "type": error_type, 
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }))
            logger.debug(f"[WS] Sent error message: {message}")
        else:
            logger.debug(f"[WS] WebSocket not connected, skipping error message")
            
        # Always try to close
        await ws.close(code=code, reason=message[:100])  # Limit reason length
        logger.debug(f"[WS] Closed WebSocket with code {code}")
        
    except Exception as e:
        logger.error(f"[WS] send_error_and_close failed: {e}")
        try:
            await ws.close()
        except Exception:
            pass  # Final cleanup attempt


@router.websocket("/ws/meetings/{meeting_id}")
async def websocket_subscriber(websocket: WebSocket, meeting_id: str, token: str = Query(...)):
    """Simplified subscriber endpoint."""
    try:
        # 1) Auth önce; başarısızsa accept ETMEDEN close:
        try:
            claims = decode_jwt_token(token)
            logger.info(f"Subscriber auth: {claims.email}")
        except SecurityError as e:
            await websocket.close(code=1008, reason=f"auth failed: {e}")  # policy violation
            return
            
        # 2) Artık kabul edebiliriz
        await websocket.accept()

        # 3) Connection manager check (artık accept sonrası)  
        current = len(ws_manager.subscriber_connections.get(meeting_id, []))
        if current >= settings.MAX_WS_CLIENTS_PER_MEETING:
            await send_error_and_close(websocket, 1013, f"Max {settings.MAX_WS_CLIENTS_PER_MEETING} connections per meeting")
            return
            
        # Register connection
        ws_manager.subscriber_connections.setdefault(meeting_id, []).append(websocket)
        ws_manager.connection_meetings[websocket] = meeting_id
        logger.info(f"📥 Subscriber connected to meeting {meeting_id}")
        await ws_manager._send_status(websocket, meeting_id, "connected", "WS connected")

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
async def websocket_ingest(websocket: WebSocket, meeting_id: str, source: str = Query("mic", regex="^(mic|sys|system)$"), token: str = Query(None)):
    """Simplified ingest endpoint with Authorization header and query token support."""
    client: Optional[DeepgramLiveClient] = None
    
    try:
        # 1) Extract token from Authorization header (preferred) or query parameter (fallback)
        jwt_token = None
        
        # Try Authorization header first (Bearer token)
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            jwt_token = auth_header[7:].strip()  # Remove "Bearer " prefix
            logger.info(f"[WS][INGEST] Using Authorization header token for meeting {meeting_id} (source: {source})")
        elif token:
            # Fallback to query parameter
            jwt_token = token.strip()
            logger.info(f"[WS][INGEST] Using query parameter token for meeting {meeting_id} (source: {source})")
        
        if not jwt_token:
            await websocket.close(code=1008, reason="auth failed: No token provided in Authorization header or query parameter")
            return
            
        # Sanitize token (remove newlines/whitespace that might cause issues)
        jwt_token = "".join(jwt_token.split())
            
        # 2) Auth validation
        try:
            claims = decode_jwt_token(jwt_token)
            logger.info(f"[WS][INGEST] Auth success: {claims.email} (meeting: {meeting_id}, source: {source})")
        except SecurityError as e:
            logger.warning(f"[WS][INGEST] Auth failed for meeting {meeting_id}: {e}")
            await websocket.close(code=1008, reason=f"auth failed: {e}")  # policy violation
            return

        # 2) Artık kabul edebiliriz
        await websocket.accept()
        logger.info(f"[WS][INGEST] WebSocket accepted for meeting {meeting_id} (source: {source})")

        # 3) Connection manager check (artık accept sonrası) - dual-source support
        connection_key = (meeting_id, source)
        if connection_key in ws_manager.ingest_connections:
            logger.warning(f"[WS][INGEST] Duplicate ingest connection for meeting {meeting_id} source {source}")
            await send_error_and_close(websocket, 1013, f"Ingest already active for this meeting (source: {source})")
            return
            
        # Register connection with (meeting_id, source) tuple
        ws_manager.ingest_connections[connection_key] = websocket
        ws_manager.connection_meetings[websocket] = connection_key
        logger.info(f"🎤 [WS][INGEST] Connected to meeting {meeting_id} (source: {source})")
        await ws_manager._send_status(websocket, meeting_id, "connected", "Ingest connected")

        # 4) Handshake oku & doğrula
        print(f"🔄 STEP 4: Reading handshake for {meeting_id}-{source}")  # DEBUG
        try:
            hs_data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            print(f"📨 HANDSHAKE DATA: {hs_data[:100]}...")  # DEBUG
            hs = IngestHandshakeMessage.model_validate_json(hs_data)
            logger.info(f"[WS][INGEST] Handshake received: source={hs.source}, rate={hs.sample_rate}, lang={hs.language}")
            print(f"✅ HANDSHAKE VALID: {hs.source}")  # DEBUG
        except Exception as e:
            logger.error(f"[WS][INGEST] Handshake failed for meeting {meeting_id}: {e}")
            print(f"❌ HANDSHAKE FAILED: {e}")  # DEBUG
            await send_error_and_close(websocket, 1002, f"Handshake invalid: {e}")
            return

        # Validate handshake
        if hs.sample_rate != settings.INGEST_SAMPLE_RATE:
            await send_error_and_close(websocket, 1002, f"Invalid sample rate {hs.sample_rate}, expected {settings.INGEST_SAMPLE_RATE}")
            return
        if hs.channels != settings.INGEST_CHANNELS:
            await send_error_and_close(websocket, 1002, f"Invalid channels {hs.channels}, expected {settings.INGEST_CHANNELS}")
            return

        # Initialize segment counter
        if meeting_id not in meeting_segments:
            meeting_segments[meeting_id] = 0

        # Deepgram callbacks
        async def on_transcript(res: dict):
            is_final = res.get("is_final", False)
            
            if is_final:
                meeting_segments[meeting_id] += 1
                
            # Normalize source: both "sys" and "system" map to "sys" for message consistency
            mapped_source = "sys" if hs.source in ["sys", "system"] else hs.source
            
            msg = create_transcript_message(
                meeting_id=meeting_id, 
                segment_no=meeting_segments[meeting_id] if is_final else meeting_segments.get(meeting_id, 0),
                text=res["text"], start_ms=res["start_ms"], end_ms=res["end_ms"], 
                is_final=is_final, speaker=res.get("speaker"),
                confidence=res.get("confidence"), source=mapped_source
            )
            
            # Store in database if final
            if is_final:
                await transcript_store.store_final_transcript(
                    meeting_id=meeting_id, segment_no=meeting_segments[meeting_id], text=res["text"],
                    start_ms=res["start_ms"], end_ms=res["end_ms"], speaker=res.get("speaker"),
                    confidence=res.get("confidence"), raw_json=res.get("raw_result")
                )
            
            # Publish to Redis with JSON serialization fix for datetime objects
            await redis_bus.publish(
                redis_bus.get_meeting_transcript_topic(meeting_id), 
                jsonable_encoder(msg.model_dump())
            )

        async def on_err(err: str):
            logger.error(f"Deepgram error: {err}")
            await ws_manager.send_to_ingest(meeting_id, source, {"type": "error", "code": "deepgram_error", "message": err})

        # Create Deepgram client with unique session ID for (meeting_id, source)
        unique_session_id = f"{meeting_id}-{source}"
        client = DeepgramLiveClient(
            meeting_id=unique_session_id, language=hs.language, sample_rate=hs.sample_rate,
            on_transcript=on_transcript, on_error=on_err
        )
        
        # 🔍 EXPLICIT DEEPGRAM CONNECTION TEST
        logger.info(f"[WS][INGEST] 🔄 ATTEMPTING Deepgram connection for {unique_session_id}...")
        print(f"🔄 BEFORE client.connect() call for {unique_session_id}")  # DEBUG
        
        try:
            print(f"🚀 CALLING client.connect() for {unique_session_id}")  # DEBUG
            await client.connect()
            print(f"🎯 client.connect() RETURNED for {unique_session_id}")  # DEBUG
            logger.info(f"[WS][INGEST] ✅ DEEPGRAM CONNECTED SUCCESSFULLY for meeting {meeting_id} (source: {source}, session: {unique_session_id})")
            print(f"🎉 DEEPGRAM CONNECTED: {unique_session_id}")  # Console output
        except Exception as e:
            print(f"💥 client.connect() EXCEPTION for {unique_session_id}: {e}")  # DEBUG
            logger.error(f"[WS][INGEST] ❌ DEEPGRAM CONNECTION FAILED for meeting {meeting_id} (source: {source}): {e}")
            print(f"💥 DEEPGRAM FAILED: {unique_session_id} - {e}")  # Console output
            await send_error_and_close(websocket, 1011, f"Deepgram connect failed: {e}")
            return

        # Send success response
        success_msg = {"status": "success", "message": "Connected to transcription", "session_id": f"sess-{unique_session_id}"}
        await websocket.send_text(json.dumps(success_msg))
        logger.info(f"[WS][INGEST] 🎉 Full setup complete for meeting {meeting_id} (source: {source})")

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
                            logger.info(f"Finalizing {meeting_id} (source: {source})")
                            await client.finalize()
                            break
                        if ctrl.type == "close":
                            break
                    except Exception as e:
                        logger.warning(f"Invalid control: {e}")
                        
            elif message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        logger.info(f"Ingest disconnected from {meeting_id} (source: {source})")
    except Exception as e:
        logger.error(f"Ingest error for {meeting_id} (source: {source}): {e}")
        
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        await ws_manager.disconnect(websocket)
        meeting_segments.pop(meeting_id, None)


@router.websocket("/transcript/{meeting_id}")
async def websocket_transcript(websocket: WebSocket, meeting_id: str):
    """
    Frontend WebSocket endpoint for receiving real-time transcripts.
    Subscribes to Redis transcript messages and forwards to frontend.
    """
    try:
        # 1) Extract JWT token from Authorization header
        jwt_token = None
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            jwt_token = auth_header[7:].strip()  # Remove "Bearer " prefix
            logger.info(f"[WS][TRANSCRIPT] Using Authorization header token for meeting {meeting_id}")
        
        if not jwt_token:
            logger.warning(f"[WS][TRANSCRIPT] No token provided for meeting {meeting_id}")
            await websocket.accept()  # Accept first to avoid HTTP 403
            await websocket.close(code=1008, reason="auth failed: No token provided in Authorization header")
            return
            
        # Sanitize token (remove newlines/whitespace that might cause issues)
        jwt_token = "".join(jwt_token.split())
            
        # 2) Auth validation
        try:
            claims = decode_jwt_token(jwt_token)
            logger.info(f"[WS][TRANSCRIPT] Auth success: {claims.email} (meeting: {meeting_id})")
        except SecurityError as e:
            logger.warning(f"[WS][TRANSCRIPT] Auth failed for meeting {meeting_id}: {e}")
            await websocket.accept()  # Accept first to avoid HTTP 403
            await websocket.close(code=1008, reason=f"auth failed: {e}")
            return

        # 3) Now we can accept the connection
        await websocket.accept()
        logger.info(f"🌐 Frontend WebSocket connected for meeting: {meeting_id}")
    except Exception as e:
        logger.error(f"[WS][TRANSCRIPT] Auth error for meeting {meeting_id}: {e}")
        try:
            await websocket.accept()  # Accept first to avoid HTTP 403
            await websocket.close(code=1008, reason=f"auth error: {e}")
        except:
            pass
        return
    
    # Register frontend connection
    if meeting_id not in frontend_connections:
        frontend_connections[meeting_id] = []
    frontend_connections[meeting_id].append(websocket)
    
    # Subscribe to Redis transcript channel
    channel = f"meeting:{meeting_id}:transcript"
    
    try:
        # Start Redis subscription in background task
        async def redis_listener():
            try:
                async for message in redis_bus.subscribe_generator(channel):
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # Forward transcript message to frontend
                        await websocket.send_text(message)
                        logger.debug(f"📤 Sent transcript to frontend: {meeting_id}")
                    else:
                        break
            except Exception as e:
                logger.error(f"Redis listener error for {meeting_id}: {e}")
        
        # Start listener task
        listener_task = asyncio.create_task(redis_listener())
        
        # Keep connection alive and handle disconnect
        try:
            while True:
                # Wait for any message from frontend (keepalive, etc.)
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps({"type": "ping"}))
                except WebSocketDisconnect:
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"🌐 Frontend WebSocket disconnected for meeting: {meeting_id}")
        finally:
            # Cancel listener task
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        logger.error(f"Frontend WebSocket error for {meeting_id}: {e}")
    finally:
        # Cleanup frontend connection
        if meeting_id in frontend_connections:
            if websocket in frontend_connections[meeting_id]:
                frontend_connections[meeting_id].remove(websocket)
            if not frontend_connections[meeting_id]:
                del frontend_connections[meeting_id]
        
        logger.info(f"🌐 Frontend WebSocket cleanup completed for meeting: {meeting_id}")


@router.get("/ws/meetings/{meeting_id}/stats")
async def get_meeting_stats(meeting_id: str):
    """Get meeting stats."""
    return ws_manager.get_meeting_stats(meeting_id)
