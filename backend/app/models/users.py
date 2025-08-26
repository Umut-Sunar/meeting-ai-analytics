"""
User model for SQLAlchemy with multi-tenancy support.
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Enum, Index, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import UserRole, UserProvider, UserStatus


class User(Base):
    """User model with tenant isolation."""
    
    __tablename__ = "users"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Basic user information
    email = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    
    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    # Authentication
    provider = Column(Enum(UserProvider), default=UserProvider.PASSWORD, nullable=False)
    provider_id = Column(String(255), nullable=True)  # OAuth provider user ID
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Status
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    # Optional profile data
    job_description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    owned_meetings = relationship("Meeting", foreign_keys="Meeting.owner_user_id", back_populates="owner")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    skill_assessments = relationship("SkillAssessment", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique email per tenant
        UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
        # Indexes for common queries
        Index('ix_users_tenant_id', 'tenant_id'),
        Index('ix_users_tenant_email', 'tenant_id', 'email'),
        Index('ix_users_provider', 'provider', 'provider_id'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id='{self.id}', email='{self.email}', tenant_id='{self.tenant_id}')>"