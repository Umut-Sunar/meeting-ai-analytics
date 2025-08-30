"""
WebSocket message schemas for real-time communication.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class BaseMessage(BaseModel):
    """Base class for all WebSocket messages."""
    type: str
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Outgoing messages to web subscribers

class TranscriptPartialMessage(BaseMessage):
    """Partial transcript message (interim results)."""
    type: Literal["transcript.partial"] = "transcript.partial"
    meeting_id: str
    source: Literal["mic", "sys", "system"] = "mic"
    segment_no: int
    start_ms: int
    end_ms: Optional[int] = None
    speaker: Optional[str] = None
    text: str
    confidence: Optional[float] = None
    meta: Dict[str, str] = Field(default_factory=dict)


class TranscriptFinalMessage(BaseMessage):
    """Final transcript message (completed segment)."""
    type: Literal["transcript.final"] = "transcript.final"
    meeting_id: str
    source: Literal["mic", "sys", "system"] = "mic"
    segment_no: int
    start_ms: int
    end_ms: int
    speaker: Optional[str] = None
    text: str
    confidence: float
    meta: Dict[str, str] = Field(default_factory=dict)


class AITipMessage(BaseMessage):
    """AI-generated tip or insight."""
    type: Literal["ai.tip"] = "ai.tip"
    meeting_id: str
    tip_type: str  # "question", "summary", "action_item", etc.
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    meta: Dict[str, str] = Field(default_factory=dict)


class StatusMessage(BaseMessage):
    """Status update message."""
    type: Literal["status"] = "status"
    meeting_id: str
    status: str  # "connected", "recording", "processing", "error", etc.
    message: Optional[str] = None
    details: Dict[str, str] = Field(default_factory=dict)


class ErrorMessage(BaseMessage):
    """Error message."""
    type: Literal["error"] = "error"
    meeting_id: str
    error_code: str
    error_message: str
    details: Dict[str, str] = Field(default_factory=dict)


# Union type for all outgoing messages
OutgoingMessage = Union[
    TranscriptPartialMessage,
    TranscriptFinalMessage,
    AITipMessage,
    StatusMessage,
    ErrorMessage
]


# Incoming messages from desktop clients

class IngestHandshakeMessage(BaseMessage):
    """Handshake message from ingest client."""
    type: Literal["handshake"] = "handshake"
    source: Literal["mic", "sys", "system"] = "mic"
    sample_rate: int = Field(default=16000, ge=8000, le=48000)  # 🚨 FIXED: Default to 16kHz
    channels: int = Field(default=1, ge=1, le=2)
    language: str = Field(default="tr")
    ai_mode: Literal["standard", "super"] = "standard"
    device_id: str
    
    @validator('language')
    def validate_language(cls, v):
        allowed = ["tr", "en", "auto", "es", "fr", "de", "it", "pt", "ru", "ja", "zh"]
        if v not in allowed:
            raise ValueError(f"Language must be one of: {allowed}")
        return v


class IngestControlMessage(BaseMessage):
    """Control message from ingest client."""
    type: Literal["finalize", "close", "pause", "resume"]
    reason: Optional[str] = None


# Union type for all incoming messages
IncomingMessage = Union[
    IngestHandshakeMessage,
    IngestControlMessage
]


# WebSocket connection info

class ConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""
    connection_id: str
    meeting_id: str
    user_id: UUID
    tenant_id: UUID
    connection_type: Literal["subscriber", "ingest"]
    connected_at: datetime
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    meta: Dict[str, str] = Field(default_factory=dict)


class IngestSessionInfo(BaseModel):
    """Information about an ingest session."""
    session_id: str
    meeting_id: str
    user_id: UUID
    tenant_id: UUID
    device_id: str
    source: str
    sample_rate: int
    channels: int
    language: str
    ai_mode: str
    started_at: datetime
    bytes_received: int = 0
    frames_received: int = 0
    deepgram_connected: bool = False
    last_activity: Optional[datetime] = None


# Rate limiting

class RateLimitBucket(BaseModel):
    """Token bucket for rate limiting."""
    tokens: float
    last_refill: datetime
    max_tokens: float
    refill_rate: float  # tokens per second
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket."""
        now = datetime.utcnow()
        
        # Refill tokens
        time_passed = (now - self.last_refill).total_seconds()
        new_tokens = time_passed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now
        
        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# Utility functions

def create_transcript_message(
    meeting_id: str,
    segment_no: int,
    text: str,
    start_ms: int,
    end_ms: Optional[int] = None,
    is_final: bool = False,
    speaker: Optional[str] = None,
    confidence: Optional[float] = None,
    source: str = "mic",
    **meta
) -> Union[TranscriptPartialMessage, TranscriptFinalMessage]:
    """Create a transcript message."""
    
    common_data = {
        "meeting_id": meeting_id,
        "source": source,
        "segment_no": segment_no,
        "text": text,
        "start_ms": start_ms,
        "speaker": speaker,
        "meta": meta
    }
    
    if is_final and end_ms is not None:
        return TranscriptFinalMessage(
            end_ms=end_ms,
            confidence=confidence or 0.0,
            **common_data
        )
    else:
        return TranscriptPartialMessage(
            end_ms=end_ms,
            confidence=confidence,
            **common_data
        )


def create_status_message(
    meeting_id: str,
    status: str,
    message: Optional[str] = None,
    **details
) -> StatusMessage:
    """Create a status message."""
    return StatusMessage(
        meeting_id=meeting_id,
        status=status,
        message=message,
        details=details
    )


def create_error_message(
    meeting_id: str,
    error_code: str,
    error_message: str,
    **details
) -> ErrorMessage:
    """Create an error message."""
    return ErrorMessage(
        meeting_id=meeting_id,
        error_code=error_code,
        error_message=error_message,
        details=details
    )
