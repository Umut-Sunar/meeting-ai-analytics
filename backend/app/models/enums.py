"""
Database enums for SQLAlchemy models.
All enums are defined here for consistency and reusability.
"""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class UserProvider(str, Enum):
    """Authentication provider enumeration."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    PASSWORD = "password"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"


class TeamRole(str, Enum):
    """Team member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    TRIAL = "trial"
    ACTIVE = "active"
    GRACE = "grace"
    CANCELLED = "cancelled"


class OveragePolicy(str, Enum):
    """Overage policy enumeration."""
    BLOCK = "block"
    PAYG = "payg"  # Pay-as-you-go


class DevicePlatform(str, Enum):
    """Device platform enumeration."""
    MACOS = "macos"
    WINDOWS = "windows"


class MeetingPlatform(str, Enum):
    """Meeting platform enumeration."""
    ZOOM = "zoom"
    TEAMS = "teams"
    MEET = "meet"
    GENERIC = "generic"


class MeetingStatus(str, Enum):
    """Meeting status enumeration."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Language(str, Enum):
    """Language enumeration."""
    TR = "tr"
    EN = "en"
    AUTO = "auto"


class AIMode(str, Enum):
    """AI processing mode enumeration."""
    STANDARD = "standard"
    SUPER = "super"


class StreamSource(str, Enum):
    """Audio stream source enumeration."""
    MICROPHONE = "microphone"
    SYSTEM = "system"


class Codec(str, Enum):
    """Audio codec enumeration."""
    LINEAR16 = "linear16"
    OPUS = "opus"
    AAC = "aac"


class MessageRole(str, Enum):
    """AI message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class SkillCategory(str, Enum):
    """Skill category enumeration."""
    SALES = "sales"
    PM = "pm"
    TECH = "tech"
    CS = "cs"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"


class AuditAction(str, Enum):
    """Audit log action enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    INVITE = "invite"
    REVOKE = "revoke"
