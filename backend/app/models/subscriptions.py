"""
Subscription and billing models for SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Index, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import SubscriptionStatus, OveragePolicy


class Plan(Base):
    """Subscription plan model (global, not tenant-specific)."""
    
    __tablename__ = "plans"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Plan details
    name = Column(String(50), nullable=False, unique=True)
    monthly_price = Column(Integer, nullable=False)  # Price in cents
    meeting_minutes_limit = Column(Integer, nullable=False)
    token_limit = Column(Integer, nullable=False)
    features = Column(JSON, default=dict, nullable=False)  # Feature flags and limits
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_plans_active', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<Plan(id='{self.id}', name='{self.name}', price={self.monthly_price})>"


class Subscription(Base):
    """Tenant subscription model."""
    
    __tablename__ = "subscriptions"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Plan reference
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    
    # Subscription status and billing
    status = Column(Enum(SubscriptionStatus), nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    overage_policy = Column(Enum(OveragePolicy), default=OveragePolicy.BLOCK, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    plan = relationship("Plan")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_subscriptions_tenant_id', 'tenant_id'),
        Index('ix_subscriptions_status', 'status'),
        Index('ix_subscriptions_period_end', 'current_period_end'),
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(id='{self.id}', tenant_id='{self.tenant_id}', status='{self.status}')>"


class Quota(Base):
    """Usage quota tracking per tenant per period."""
    
    __tablename__ = "quotas"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Period tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Usage tracking
    minutes_used = Column(Integer, default=0, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    overage_minutes = Column(Integer, default=0, nullable=False)
    overage_tokens = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_quotas_tenant_period', 'tenant_id', 'period_start', 'period_end'),
        Index('ix_quotas_period_end', 'period_end'),
    )
    
    def __repr__(self) -> str:
        return f"<Quota(tenant_id='{self.tenant_id}', minutes={self.minutes_used}, tokens={self.tokens_used})>"