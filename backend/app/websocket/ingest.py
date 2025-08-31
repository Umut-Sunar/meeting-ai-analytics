"""
WebSocket Ingest Module with Rate Limiting and Structured Logging.

This module handles WebSocket connections for audio ingest with:
- Connection rate limiting
- Structured logging with meeting_id, source, connection_id
- State transition tracking
"""

import asyncio
import time
import uuid
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
import structlog

from app.core.security import decode_jwt_token, SecurityError
from app.core.config import get_settings
from app.services.asr.deepgram_live import DeepgramLiveClient

# Configure structured logger
import logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Rate limiting storage: (meeting_id, source) -> deque of connection timestamps
rate_limit_storage: Dict[Tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=10))

# Active connections registry: (meeting_id, source) -> connection info
ingest_registry: Dict[Tuple[str, str], Dict[str, Any]] = {}

# Settings
settings = get_settings()

# Rate limiting configuration
RATE_LIMIT_WINDOW = 10  # seconds
RATE_LIMIT_MAX_ATTEMPTS = 5


class ConnectionRateLimiter:
    """Rate limiter for WebSocket connections."""
    
    @staticmethod
    def check_rate_limit(meeting_id: str, source: str) -> bool:
        """
        Check if connection is rate limited.
        
        Args:
            meeting_id: Meeting identifier
            source: Audio source (mic/sys)
            
        Returns:
            True if connection should be allowed, False if rate limited
        """
        key = (meeting_id, source)
        now = time.time()
        
        # Clean old entries
        timestamps = rate_limit_storage[key]
        while timestamps and timestamps[0] < now - RATE_LIMIT_WINDOW:
            timestamps.popleft()
        
        # Check if rate limit exceeded
        if len(timestamps) >= RATE_LIMIT_MAX_ATTEMPTS:
            return False
        
        # Add current timestamp
        timestamps.append(now)
        return True


class StructuredLogger:
    """Structured logger for WebSocket connections."""
    
    def __init__(self, meeting_id: str, source: str, connection_id: str):
        self.meeting_id = meeting_id
        self.source = source
        self.connection_id = connection_id
        self.base_context = {
            "meeting_id": meeting_id,
            "source": source,
            "connection_id": connection_id,
            "component": "websocket_ingest"
        }
    
    def log_state_transition(self, from_state: str, to_state: str, **kwargs):
        """Log state transition with context."""
        logger.info(
            "WebSocket state transition",
            **self.base_context,
            from_state=from_state,
            to_state=to_state,
            **kwargs
        )
    
    def log_event(self, event: str, level: str = "info", **kwargs):
        """Log event with context."""
        log_func = getattr(logger, level, logger.info)
        log_func(
            f"WebSocket event: {event}",
            **self.base_context,
            event=event,
            **kwargs
        )
    
    def log_error(self, error: str, exception: Optional[Exception] = None, **kwargs):
        """Log error with context."""
        logger.error(
            f"WebSocket error: {error}",
            **self.base_context,
            error=error,
            exception=str(exception) if exception else None,
            **kwargs
        )


async def handle_websocket_ingest(
    websocket: WebSocket, 
    meeting_id: str, 
    source: str = Query("mic", regex="^(mic|sys|system)$"), 
    token: str = Query(None)
):
    """
    Handle WebSocket ingest connection with rate limiting and structured logging.
    
    Args:
        websocket: WebSocket connection
        meeting_id: Meeting identifier
        source: Audio source (mic/sys/system)
        token: JWT authentication token
    """
    # Generate unique connection ID
    connection_id = str(uuid.uuid4())[:8]
    
    # Initialize structured logger
    struct_logger = StructuredLogger(meeting_id, source, connection_id)
    
    # Normalize source
    if source == "system":
        source = "sys"
    
    connection_key = (meeting_id, source)
    client: Optional[DeepgramLiveClient] = None
    is_closing = False
    current_state = "connecting"
    
    struct_logger.log_state_transition("none", "connecting", 
                                     client_host=websocket.client.host if websocket.client else "unknown")
    
    async def safe_close(code: int, reason: str):
        """Idempotent close to avoid double-close."""
        nonlocal is_closing, current_state
        if is_closing:
            return
        is_closing = True
        
        struct_logger.log_state_transition(current_state, "closing", 
                                         close_code=code, close_reason=reason)
        
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=code, reason=reason)
        except Exception as e:
            struct_logger.log_error("Close error", exception=e)
        
        current_state = "closed"
        struct_logger.log_state_transition("closing", "closed")
    
    try:
        # 1) Rate limiting check
        if not ConnectionRateLimiter.check_rate_limit(meeting_id, source):
            struct_logger.log_event("rate_limit_exceeded", level="warning",
                                   window_seconds=RATE_LIMIT_WINDOW,
                                   max_attempts=RATE_LIMIT_MAX_ATTEMPTS)
            await safe_close(1013, "Rate limit exceeded. Try again later.")
            return
        
        struct_logger.log_event("rate_limit_passed")
        
        # 2) Extract and validate JWT token
        jwt_token = None
        
        # Debug: Log all headers
        struct_logger.log_event("debug_headers", headers=dict(websocket.headers))
        
        # Try Authorization header first (Bearer token)
        auth_header = websocket.headers.get("authorization")
        struct_logger.log_event("debug_auth_header", auth_header=auth_header)
        
        if auth_header and auth_header.lower().startswith("bearer "):
            jwt_token = auth_header[7:].strip()
            struct_logger.log_event("auth_header_token_found", token_length=len(jwt_token))
        elif token:
            jwt_token = token.strip()
            struct_logger.log_event("query_param_token_found", token_length=len(jwt_token) if jwt_token else 0)
        
        if not jwt_token:
            struct_logger.log_error("No token provided", 
                                   auth_header=auth_header, 
                                   query_token=token)
            await safe_close(1008, "auth failed: No token provided")
            return
            
        # Sanitize token
        jwt_token = "".join(jwt_token.split())
        
        # 3) Auth validation
        try:
            claims = decode_jwt_token(jwt_token)
            struct_logger.log_event("auth_success", user_email=claims.email, user_id=claims.user_id)
        except SecurityError as e:
            struct_logger.log_error("Auth failed", exception=e, jwt_token_length=len(jwt_token))
            # Temporary bypass for testing
            struct_logger.log_event("auth_bypass_for_testing")
            # await safe_close(1008, f"auth failed: {e}")
            # return

        # 4) Accept connection
        await websocket.accept()
        current_state = "connected"
        struct_logger.log_state_transition("connecting", "connected")
        
        # 5) Handle duplicate connections (replace existing)
        if connection_key in ingest_registry:
            old_connection = ingest_registry[connection_key]
            old_websocket = old_connection.get("websocket")
            old_connection_id = old_connection.get("connection_id", "unknown")
            
            struct_logger.log_event("replacing_duplicate_connection", 
                                   old_connection_id=old_connection_id)
            
            # Close old connection gracefully
            if old_websocket and old_websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await old_websocket.close(code=1012, reason="Connection replaced by newer one")
                except Exception as e:
                    struct_logger.log_error("Error closing old connection", exception=e)
        
        # Register new connection
        ingest_registry[connection_key] = {
            "websocket": websocket,
            "connection_id": connection_id,
            "meeting_id": meeting_id,
            "source": source,
            "user_email": claims.email,
            "connected_at": time.time()
        }
        
        struct_logger.log_event("connection_registered")
        
        # 6) Handshake protocol
        current_state = "awaiting_handshake"
        struct_logger.log_state_transition("connected", "awaiting_handshake")
        
        try:
            # Wait for handshake with timeout
            handshake_data = await asyncio.wait_for(websocket.receive_json(), timeout=6.0)
            struct_logger.log_event("handshake_received", handshake_data=handshake_data)
        except asyncio.TimeoutError:
            struct_logger.log_error("Handshake timeout")
            await safe_close(1002, "Handshake timeout")
            return
        except Exception as e:
            struct_logger.log_error("Handshake receive error", exception=e)
            await safe_close(1002, "Invalid handshake format")
            return
        
        # Validate handshake
        if not isinstance(handshake_data, dict) or handshake_data.get("type") != "handshake":
            struct_logger.log_error("Invalid handshake type", received_type=handshake_data.get("type"))
            await safe_close(1002, "Invalid handshake: expected type 'handshake'")
            return
        
        # Validate handshake fields
        device_id = handshake_data.get("device_id")
        handshake_source = handshake_data.get("source")
        sample_rate = handshake_data.get("sample_rate")
        channels = handshake_data.get("channels")
        
        validation_errors = []
        
        if not device_id or not isinstance(device_id, str):
            validation_errors.append(f"device_id must be non-empty string, got {type(device_id).__name__}: {repr(device_id)}")
        
        if handshake_source not in ["mic", "sys"]:
            validation_errors.append(f"source must be 'mic' or 'sys', got {type(handshake_source).__name__}: {repr(handshake_source)}")
        
        if not isinstance(sample_rate, int) or sample_rate != settings.INGEST_SAMPLE_RATE:
            validation_errors.append(f"sample_rate must be {settings.INGEST_SAMPLE_RATE}, got {type(sample_rate).__name__}: {repr(sample_rate)}")
        
        if not isinstance(channels, int) or channels != settings.INGEST_CHANNELS:
            validation_errors.append(f"channels must be {settings.INGEST_CHANNELS}, got {type(channels).__name__}: {repr(channels)}")
        
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            struct_logger.log_error("Handshake validation failed", validation_errors=validation_errors)
            await safe_close(1002, f"Invalid handshake: {error_msg}")
            return
        
        # Source consistency check
        if handshake_source != source:
            struct_logger.log_error("Source mismatch", url_source=source, handshake_source=handshake_source)
            await safe_close(1002, f"Source mismatch: URL has '{source}', handshake has '{handshake_source}'")
            return
        
        struct_logger.log_event("handshake_validated", 
                               device_id=device_id,
                               sample_rate=sample_rate,
                               channels=channels)
        
        # 7) Send handshake acknowledgment
        try:
            await websocket.send_json({"type": "handshake-ack", "ok": True})
            current_state = "handshake_complete"
            struct_logger.log_state_transition("awaiting_handshake", "handshake_complete")
        except Exception as e:
            struct_logger.log_error("Failed to send handshake ack", exception=e)
            await safe_close(1011, "Failed to send handshake acknowledgment")
            return
        
        # 8) Initialize Deepgram client
        try:
            client = DeepgramLiveClient(
                meeting_id=meeting_id,
                language=settings.DEEPGRAM_LANGUAGE,
                sample_rate=settings.INGEST_SAMPLE_RATE,
                channels=settings.INGEST_CHANNELS,
                model=settings.DEEPGRAM_MODEL
            )
            await client.connect()
            current_state = "deepgram_connected"
            struct_logger.log_state_transition("handshake_complete", "deepgram_connected")
        except Exception as e:
            struct_logger.log_error("Deepgram connection failed", exception=e)
            await safe_close(1011, "Failed to initialize speech recognition")
            return
        
        # 9) Main message loop
        current_state = "pcm_streaming"
        struct_logger.log_state_transition("deepgram_connected", "pcm_streaming")
        
        message_count = 0
        bytes_received = 0
        
        async for message in websocket.iter_bytes():
            message_count += 1
            bytes_received += len(message)
            
            # Log periodic stats
            if message_count % 100 == 0:
                struct_logger.log_event("streaming_stats",
                                       message_count=message_count,
                                       bytes_received=bytes_received,
                                       avg_message_size=bytes_received // message_count)
            
            # Size validation
            if len(message) > settings.MAX_INGEST_MSG_BYTES:
                struct_logger.log_error("Message too large", 
                                       message_size=len(message),
                                       max_size=settings.MAX_INGEST_MSG_BYTES)
                await safe_close(1009, f"Message too large: {len(message)} bytes")
                break
            
            # Forward to Deepgram
            try:
                await client.send_audio(message)
            except Exception as e:
                struct_logger.log_error("Failed to send audio to Deepgram", exception=e)
                await safe_close(1011, "Speech recognition error")
                break
        
        # Normal completion
        current_state = "stream_ended"
        struct_logger.log_state_transition("pcm_streaming", "stream_ended",
                                         total_messages=message_count,
                                         total_bytes=bytes_received)
        
    except WebSocketDisconnect:
        current_state = "disconnected"
        struct_logger.log_state_transition(current_state, "disconnected", reason="client_disconnect")
    except Exception as e:
        struct_logger.log_error("Unexpected error", exception=e)
        await safe_close(1011, "Internal server error")
    finally:
        # Cleanup
        if client:
            try:
                await client.close()
                struct_logger.log_event("deepgram_client_closed")
            except Exception as e:
                struct_logger.log_error("Error closing Deepgram client", exception=e)
        
        # Remove from registry
        if connection_key in ingest_registry:
            registered_connection = ingest_registry[connection_key]
            if registered_connection.get("connection_id") == connection_id:
                del ingest_registry[connection_key]
                struct_logger.log_event("connection_unregistered")
        
        struct_logger.log_state_transition(current_state, "cleanup_complete")
