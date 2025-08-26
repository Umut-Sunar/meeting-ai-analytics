"""
Device and client management models.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import DevicePlatform


class Device(Base):
    """Desktop client device registration."""
    
    __tablename__ = "devices"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Device information
    platform = Column(Enum(DevicePlatform), nullable=False)
    machine_fingerprint = Column(String(255), nullable=False)  # Unique machine identifier
    app_version = Column(String(50), nullable=False)
    
    # Activity tracking
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_devices_user_id', 'user_id'),
        Index('ix_devices_fingerprint', 'machine_fingerprint'),
        Index('ix_devices_last_seen', 'last_seen_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Device(id='{self.id}', user_id='{self.user_id}', platform='{self.platform}')>"