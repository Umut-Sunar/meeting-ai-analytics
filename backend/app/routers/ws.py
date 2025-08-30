"""
Simplified WebSocket endpoints.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Tuple, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketState
from pydantic import ValidationError

from app.core.security import decode_jwt_token, SecurityError
from app.services.ws.connection import ws_manager
from app.services.ws.messages import (
    IngestHandshakeMessage, IngestControlMessage, 
    create_transcript_message, create_status_message, create_error_message,
    TranscriptFinalMessage, TranscriptPartialMessage
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


# Global registry for ingest connections - keyed by (meeting_id, source)
ingest_registry: Dict[Tuple[str, str], Dict[str, Any]] = {}

@router.websocket("/ws/ingest/meetings/{meeting_id}")
async def websocket_ingest(websocket: WebSocket, meeting_id: str, source: str = Query("mic", regex="^(mic|sys|system)$"), token: str = Query(None)):
    """WebSocket ingest endpoint with handshake protocol and duplicate replacement."""
    client: Optional[DeepgramLiveClient] = None
    is_closing = False
    connection_key = (meeting_id, source)
    
    async def safe_close(code: int, reason: str):
        """Idempotent close to avoid double-close."""
        nonlocal is_closing
        if is_closing:
            return
        is_closing = True
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"[WS][INGEST] Close error: {e}")
    
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
            await safe_close(1008, "auth failed: No token provided in Authorization header or query parameter")
            return
            
        # Sanitize token (remove newlines/whitespace that might cause issues)
        jwt_token = "".join(jwt_token.split())
            
        # 2) Auth validation
        try:
            claims = decode_jwt_token(jwt_token)
            logger.info(f"[WS][INGEST] Auth success: {claims.email} (meeting: {meeting_id}, source: {source})")
        except SecurityError as e:
            logger.warning(f"[WS][INGEST] Auth failed for meeting {meeting_id}: {e}")
            await safe_close(1008, f"auth failed: {e}")
            return

        # 3) Accept connection
        await websocket.accept()
        logger.info(f"[WS][INGEST] WebSocket accepted for meeting {meeting_id} (source: {source})")

        # 4) First frame must be handshake with timeout
        try:
            msg = await asyncio.wait_for(websocket.receive_json(), timeout=6.0)
        except asyncio.TimeoutError:
            logger.warning(f"[WS][INGEST] Handshake timeout for meeting {meeting_id} (source: {source})")
            await safe_close(1002, "handshake-timeout")
            return
        except Exception as e:
            logger.warning(f"[WS][INGEST] Handshake receive error for meeting {meeting_id}: {e}")
            await safe_close(1002, "handshake-error")
            return

        # Validate first frame is handshake
        if msg.get("type") != "handshake":
            logger.warning(f"[WS][INGEST] Invalid first frame: expected 'handshake', got: {msg.get('type')} for meeting {meeting_id}")
            await safe_close(1002, "expected-handshake")
            return

        # Validate handshake fields
        device_id = msg.get("device_id")
        handshake_source = msg.get("source")
        sample_rate = msg.get("sample_rate")
        channels = msg.get("channels")

        if not isinstance(device_id, str) or not device_id:
            logger.warning(f"[WS][INGEST] Invalid device_id in handshake: {device_id}")
            await safe_close(1002, "invalid-device-id")
            return

        if handshake_source not in {"mic", "sys"}:
            logger.warning(f"[WS][INGEST] Invalid source in handshake: {handshake_source}")
            await safe_close(1002, "invalid-source")
            return

        if not isinstance(sample_rate, int) or sample_rate != settings.INGEST_SAMPLE_RATE:
            logger.warning(f"[WS][INGEST] Invalid sample_rate: {sample_rate}, expected {settings.INGEST_SAMPLE_RATE}")
            await safe_close(1002, f"invalid-sample-rate")
            return

        if not isinstance(channels, int) or channels != settings.INGEST_CHANNELS:
            logger.warning(f"[WS][INGEST] Invalid channels: {channels}, expected {settings.INGEST_CHANNELS}")
            await safe_close(1002, f"invalid-channels")
            return

        logger.info(f"[WS][INGEST] Valid handshake: device_id={device_id}, source={handshake_source}, rate={sample_rate}, channels={channels}")

        # 5) Registry check - replace duplicates
        if connection_key in ingest_registry:
            old_entry = ingest_registry[connection_key]
            old_ws = old_entry.get("websocket")
            if old_ws and not old_entry.get("is_closing", False):
                logger.info(f"[WS][INGEST] Replacing existing connection for {meeting_id} (source: {source})")
                old_entry["is_closing"] = True
                try:
                    if old_ws.client_state != WebSocketState.DISCONNECTED:
                        await old_ws.close(code=1012, reason="replaced")
                except Exception as e:
                    logger.warning(f"[WS][INGEST] Error closing old connection: {e}")

        # Register new connection
        ingest_registry[connection_key] = {
            "websocket": websocket,
            "device_id": device_id,
            "source": handshake_source,
            "sample_rate": sample_rate,
            "channels": channels,
            "is_closing": False
        }

        # Also register in connection manager for compatibility
        ws_manager.ingest_connections[connection_key] = websocket
        ws_manager.connection_meetings[websocket] = connection_key

        # 6) Send handshake acknowledgment
        await websocket.send_json({"type": "handshake-ack", "ok": True})
        logger.info(f"🎤 [WS][INGEST] Handshake complete for meeting {meeting_id} (source: {handshake_source})")

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

            # 🚨 TASK 4: Enhanced dual-source logging
            logger.info(f"[DUAL-SOURCE] Processing transcript - Meeting: {meeting_id}, Source: {mapped_source}, Text: {res['text'][:50]}...")

            msg = create_transcript_message(
                meeting_id=meeting_id, 
                segment_no=meeting_segments[meeting_id] if is_final else meeting_segments.get(meeting_id, 0),
                text=res["text"], start_ms=res["start_ms"], end_ms=res["end_ms"], 
                is_final=is_final, speaker=res.get("speaker"),
                confidence=res.get("confidence"), source=mapped_source
            )
            
            # Store in database if final
            if is_final:
                # Generate deepgram_stream_id from meeting_id and source for idempotent key
                deepgram_stream_id = f"{meeting_id}_{mapped_source}"
                
                await transcript_store.store_final_transcript(
                    meeting_id=meeting_id, 
                    segment_no=meeting_segments[meeting_id], 
                    transcript_text=res["text"],
                    start_ms=res["start_ms"], 
                    end_ms=res["end_ms"], 
                    deepgram_stream_id=deepgram_stream_id,
                    speaker=res.get("speaker"),
                    confidence=res.get("confidence"), 
                    raw_json=res.get("raw_result")
                )
            
            # Publish to Redis with schema validation
            topic = redis_bus.get_meeting_transcript_topic(meeting_id)
            try:
                # Validate message before publishing
                if is_final:
                    validated_msg = TranscriptFinalMessage.model_validate(msg.model_dump())
                else:
                    validated_msg = TranscriptPartialMessage.model_validate(msg.model_dump())
                
                # Publish validated message
                await redis_bus.publish(topic, jsonable_encoder(validated_msg.model_dump()))
                logger.debug(f"✅ Published validated {'final' if is_final else 'partial'} transcript to Redis: {meeting_id}")
                
            except ValidationError as e:
                # Log validation error
                logger.error(f"❌ Schema validation failed for transcript message: {e}")
                logger.error(f"📄 Invalid message data: {msg.model_dump()}")
                
                # Publish to error channel
                error_data = {
                    "error_type": "schema_validation_failed",
                    "error_message": str(e),
                    "meeting_id": meeting_id,
                    "source": mapped_source,
                    "segment_no": meeting_segments[meeting_id] if is_final else meeting_segments.get(meeting_id, 0),
                    "is_final": is_final,
                    "timestamp": jsonable_encoder(msg.ts) if hasattr(msg, 'ts') else None,
                    "raw_data": msg.model_dump()
                }
                
                await redis_bus.publish(f"{topic}:errors", error_data)
                logger.info(f"📤 Published validation error to error channel: {topic}:errors")
                
            except Exception as e:
                # Handle other publish errors
                logger.error(f"❌ Failed to publish transcript message: {e}")
                error_data = {
                    "error_type": "publish_failed",
                    "error_message": str(e),
                    "meeting_id": meeting_id,
                    "source": mapped_source,
                    "timestamp": jsonable_encoder(msg.ts) if hasattr(msg, 'ts') else None
                }
                
                try:
                    await redis_bus.publish(f"{topic}:errors", error_data)
                except Exception as publish_error:
                    logger.error(f"❌ Failed to publish to error channel: {publish_error}")

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
        # Cleanup registry entry
        if connection_key in ingest_registry:
            ingest_registry[connection_key]["is_closing"] = True
            ingest_registry.pop(connection_key, None)
            
        # Cleanup Deepgram client
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
                
        # Cleanup connection manager
        await ws_manager.disconnect(websocket)
        meeting_segments.pop(meeting_id, None)
        
        logger.info(f"[WS][INGEST] Cleanup complete for meeting {meeting_id} (source: {source})")


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
                # Check if Redis is available
                if not redis_bus.redis:
                    logger.warning(f"Redis not connected - transcript streaming disabled for {meeting_id}")
                    return
                    
                async for message in redis_bus.subscribe_generator(channel):
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # Forward transcript message to frontend
                        await websocket.send_text(message)
                        logger.debug(f"📤 Sent transcript to frontend: {meeting_id}")
                    else:
                        break
            except Exception as e:
                logger.error(f"Redis listener error for {meeting_id}: {e}")
                # Send error message to frontend
                if websocket.client_state == WebSocketState.CONNECTED:
                    error_msg = json.dumps({
                        "type": "error",
                        "message": "Transcript streaming unavailable - Redis connection failed"
                    })
                    try:
                        await websocket.send_text(error_msg)
                    except:
                        pass
        
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
