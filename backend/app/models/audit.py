"""
Audit logging and system tracking models.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON, Date, Integer, Float, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.database.connection import Base
from app.models.enums import AuditAction


class AuditLog(Base):
    """System audit log with tenant isolation."""
    
    __tablename__ = "audit_logs"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Actor (who performed the action)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Nullable for system actions
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    target_type = Column(String(50), nullable=False)  # e.g., "user", "meeting", "team"
    target_id = Column(UUID(as_uuid=True), nullable=True)  # ID of the affected resource
    
    # Additional metadata
    meta = Column(JSON, default=dict, nullable=False)  # Action-specific metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    actor = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_audit_logs_tenant_id', 'tenant_id'),
        Index('ix_audit_logs_actor_user_id', 'actor_user_id'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_target', 'target_type', 'target_id'),
        Index('ix_audit_logs_created_at', 'created_at'),
        Index('ix_audit_logs_tenant_created', 'tenant_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', target='{self.target_type}:{self.target_id}')>"


class AnalyticsDaily(Base):
    """Daily analytics roll-up per tenant."""
    
    __tablename__ = "analytics_daily"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Date for the analytics
    date = Column(Date, nullable=False)
    
    # Meeting statistics
    meetings_count = Column(Integer, default=0, nullable=False)
    minutes_total = Column(Integer, default=0, nullable=False)
    
    # Quality metrics
    avg_confidence = Column(Float, nullable=True)  # Average transcript confidence
    avg_response_latency_ms = Column(Integer, nullable=True)  # Average AI response time
    
    # Aggregated data
    top_skills = Column(JSON, default=dict, nullable=False)  # Top performing skills
    usage_by_user = Column(JSON, default=dict, nullable=False)  # Usage breakdown by user
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_analytics_daily_tenant_date', 'tenant_id', 'date'),
        Index('ix_analytics_daily_date', 'date'),
    )
    
    def __repr__(self) -> str:
        return f"<AnalyticsDaily(tenant_id='{self.tenant_id}', date='{self.date}', meetings={self.meetings_count})>"


class APIKey(Base):
    """API keys for desktop client authentication."""
    
    __tablename__ = "api_keys"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key details
    label = Column(String(100), nullable=False)  # Human-readable label
    hash = Column(String(255), nullable=False, unique=True)  # Hashed API key
    scopes = Column(JSON, default=list, nullable=False)  # Permissions/scopes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)  # Null if active
    
    # Relationships
    user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_api_keys_tenant_id', 'tenant_id'),
        Index('ix_api_keys_user_id', 'user_id'),
        Index('ix_api_keys_hash', 'hash'),
        Index('ix_api_keys_revoked', 'revoked_at'),
    )
    
    def __repr__(self) -> str:
        return f"<APIKey(id='{self.id}', user_id='{self.user_id}', label='{self.label}')>"


class Webhook(Base):
    """Webhook endpoints for tenant integrations."""
    
    __tablename__ = "webhooks"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Webhook configuration
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)  # HMAC secret for verification
    event_types = Column(ARRAY(String), default=list, nullable=False)  # Event types to send
    
    # Activity tracking
    last_delivery_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_webhooks_tenant_id', 'tenant_id'),
        Index('ix_webhooks_last_delivery', 'last_delivery_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Webhook(id='{self.id}', tenant_id='{self.tenant_id}', url='{self.url}')>"