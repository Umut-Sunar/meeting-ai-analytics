"""
Team models for SQLAlchemy with multi-tenancy support.
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import TeamRole


class Team(Base):
    """Team model with tenant isolation."""
    
    __tablename__ = "teams"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Team information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique team name per tenant
        UniqueConstraint('tenant_id', 'name', name='uq_teams_tenant_name'),
        # Indexes for common queries
        Index('ix_teams_tenant_id', 'tenant_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Team(id='{self.id}', name='{self.name}', tenant_id='{self.tenant_id}')>"


class TeamMember(Base):
    """Junction table for team memberships."""
    
    __tablename__ = "team_members"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Role in team
    role_in_team = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique user per team
        UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
        # Indexes for common queries
        Index('ix_team_members_team_id', 'team_id'),
        Index('ix_team_members_user_id', 'user_id'),
    )
    
    def __repr__(self) -> str:
        return f"<TeamMember(team_id='{self.team_id}', user_id='{self.user_id}', role='{self.role_in_team}')>"


# Add back_populates to models
Team.members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")