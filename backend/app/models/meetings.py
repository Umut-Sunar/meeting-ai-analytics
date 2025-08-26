"""
Meeting and related models for SQLAlchemy with multi-tenancy support.
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Index, Boolean, Float, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import MeetingPlatform, MeetingStatus, Language, AIMode, StreamSource, Codec, MessageRole


class Meeting(Base):
    """Meeting model with tenant isolation."""
    
    __tablename__ = "meetings"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Relationships
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)  # Optional team association
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Meeting details
    title = Column(String(200), nullable=False)
    platform = Column(Enum(MeetingPlatform), default=MeetingPlatform.GENERIC, nullable=False)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    # Status and processing
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED, nullable=False)
    language = Column(Enum(Language), default=Language.AUTO, nullable=False)
    ai_mode = Column(Enum(AIMode), default=AIMode.STANDARD, nullable=False)
    
    # Tags
    tags = Column(ARRAY(String), default=list, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    team = relationship("Team")
    owner = relationship("User")
    streams = relationship("MeetingStream", back_populates="meeting", cascade="all, delete-orphan")
    audio_blobs = relationship("AudioBlob", back_populates="meeting", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    ai_messages = relationship("AIMessage", back_populates="meeting", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_meetings_tenant_id', 'tenant_id'),
        Index('ix_meetings_owner_user_id', 'owner_user_id'),
        Index('ix_meetings_team_id', 'team_id'),
        Index('ix_meetings_status', 'status'),
        Index('ix_meetings_start_time', 'start_time'),
        Index('ix_meetings_tenant_start_time', 'tenant_id', 'start_time'),
    )
    
    def __repr__(self) -> str:
        return f"<Meeting(id='{self.id}', title='{self.title}', status='{self.status}')>"


class MeetingStream(Base):
    """Audio stream metadata for each recording source."""
    
    __tablename__ = "meeting_streams"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Meeting reference
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    
    # Stream configuration
    source = Column(Enum(StreamSource), nullable=False)
    sample_rate = Column(Integer, nullable=False)  # Hz
    channels = Column(Integer, nullable=False)     # 1 for mono, 2 for stereo
    codec = Column(Enum(Codec), default=Codec.LINEAR16, nullable=False)
    
    # WebSocket endpoint for live streaming
    ws_endpoint = Column(Text, nullable=True)
    
    # Statistics
    bytes_in = Column(BigInteger, default=0, nullable=False)
    packets_in = Column(Integer, default=0, nullable=False)
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    stopped_at = Column(DateTime, nullable=True)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="streams")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_meeting_streams_meeting_id', 'meeting_id'),
        Index('ix_meeting_streams_source', 'meeting_id', 'source'),
    )
    
    def __repr__(self) -> str:
        return f"<MeetingStream(meeting_id='{self.meeting_id}', source='{self.source}')>"


class AudioBlob(Base):
    """S3 audio blob metadata and indexing."""
    
    __tablename__ = "audio_blobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Meeting and source reference
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    source = Column(Enum(StreamSource), nullable=False)
    
    # S3 storage
    s3_key = Column(String(500), nullable=False)
    
    # Audio metadata
    duration_ms = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    part_no = Column(Integer, nullable=False)  # Sequential part number
    checksum = Column(String(64), nullable=False)  # SHA-256 or MD5
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="audio_blobs")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_audio_blobs_meeting_id', 'meeting_id'),
        Index('ix_audio_blobs_s3_key', 's3_key'),
        Index('ix_audio_blobs_meeting_part', 'meeting_id', 'part_no'),
    )
    
    def __repr__(self) -> str:
        return f"<AudioBlob(meeting_id='{self.meeting_id}', part={self.part_no}, size={self.size_bytes})>"


class Transcript(Base):
    """Transcription segments with speaker diarization."""
    
    __tablename__ = "transcripts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Meeting reference
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    
    # Segment metadata
    segment_no = Column(Integer, nullable=False)  # Sequential segment number
    speaker = Column(String(50), nullable=False)  # Auto diarization speaker ID
    
    # Transcript content
    text = Column(Text, nullable=False)
    
    # Timing (milliseconds)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    
    # Processing status
    is_final = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Raw metadata from speech recognition
    raw_json = Column(JSON, nullable=True)  # macOS Results/Metadata JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="transcripts")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_transcripts_meeting_id', 'meeting_id'),
        Index('ix_transcripts_meeting_segment', 'meeting_id', 'segment_no'),
        Index('ix_transcripts_speaker', 'meeting_id', 'speaker'),
        Index('ix_transcripts_timing', 'meeting_id', 'start_ms', 'end_ms'),
    )
    
    def __repr__(self) -> str:
        return f"<Transcript(meeting_id='{self.meeting_id}', segment={self.segment_no}, speaker='{self.speaker}')>"


class AIMessage(Base):
    """AI conversation messages for each meeting."""
    
    __tablename__ = "ai_messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Meeting reference
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    
    # Message metadata
    turn_no = Column(Integer, nullable=False)  # Sequential turn number
    role = Column(Enum(MessageRole), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)  # Function calls and responses
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="ai_messages")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_ai_messages_meeting_id', 'meeting_id'),
        Index('ix_ai_messages_meeting_turn', 'meeting_id', 'turn_no'),
        Index('ix_ai_messages_role', 'meeting_id', 'role'),
    )
    
    def __repr__(self) -> str:
        return f"<AIMessage(meeting_id='{self.meeting_id}', turn={self.turn_no}, role='{self.role}')>"