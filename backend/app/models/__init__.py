"""
SQLAlchemy models for the Meeting AI Analytics system.

All models are imported here to ensure they are registered with SQLAlchemy
when Alembic runs autogenerate migrations.
"""

# Import all models to register them with SQLAlchemy
from app.models.enums import *  # All enums
from app.models.users import User
from app.models.teams import Team, TeamMember
from app.models.subscriptions import Plan, Subscription, Quota
from app.models.meetings import Meeting, MeetingStream, AudioBlob, Transcript, AIMessage
from app.models.devices import Device
from app.models.skills import Skill, SkillAssessment
from app.models.documents import Document
from app.models.audit import AuditLog, AnalyticsDaily, APIKey, Webhook

# Export all models for easy import
__all__ = [
    # Core models
    "User",
    "Team", 
    "TeamMember",
    
    # Billing and subscriptions
    "Plan",
    "Subscription", 
    "Quota",
    
    # Meetings and audio
    "Meeting",
    "MeetingStream",
    "AudioBlob", 
    "Transcript",
    "AIMessage",
    
    # Devices and authentication
    "Device",
    "APIKey",
    
    # Skills and assessments
    "Skill",
    "SkillAssessment",
    
    # Documents and storage
    "Document",
    
    # Audit and analytics
    "AuditLog",
    "AnalyticsDaily",
    "Webhook",
]
