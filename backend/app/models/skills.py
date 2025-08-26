"""
Skills and assessment models for user performance tracking.
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base
from app.models.enums import SkillCategory


class Skill(Base):
    """Skill definition with tenant isolation."""
    
    __tablename__ = "skills"
    
    # Primary key and tenant
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Skill information
    name = Column(String(100), nullable=False)
    category = Column(Enum(SkillCategory), nullable=False)
    description = Column(Text, nullable=True)
    rubric = Column(JSON, default=dict, nullable=False)  # Scoring criteria and rubric
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    assessments = relationship("SkillAssessment", back_populates="skill", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_skills_tenant_id', 'tenant_id'),
        Index('ix_skills_category', 'tenant_id', 'category'),
    )
    
    def __repr__(self) -> str:
        return f"<Skill(id='{self.id}', name='{self.name}', category='{self.category}')>"


class SkillAssessment(Base):
    """Individual skill assessment results per user per meeting."""
    
    __tablename__ = "skill_assessments"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    
    # Assessment results
    score = Column(Integer, nullable=False)  # 0-100
    evidence = Column(Text, nullable=True)  # Supporting evidence/examples
    improvement_notes = Column(Text, nullable=True)  # Suggestions for improvement
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User")
    meeting = relationship("Meeting")
    skill = relationship("Skill", back_populates="assessments")
    
    # Table constraints and indexes
    __table_args__ = (
        Index('ix_skill_assessments_user_id', 'user_id'),
        Index('ix_skill_assessments_meeting_id', 'meeting_id'),
        Index('ix_skill_assessments_skill_id', 'skill_id'),
        Index('ix_skill_assessments_user_skill', 'user_id', 'skill_id'),
    )
    
    def __repr__(self) -> str:
        return f"<SkillAssessment(user_id='{self.user_id}', skill_id='{self.skill_id}', score={self.score})>"