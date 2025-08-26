"""
User-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "Admin"
    MANAGER = "Manager"
    MEMBER = "Member"


class UserPlan(str, Enum):
    """User subscription plan enumeration."""
    FREE = "Free"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "Active"
    SUSPENDED = "Suspended"


class UserUsage(BaseModel):
    """User usage statistics."""
    minutes: int = Field(..., ge=0, description="Used minutes")
    max_minutes: int = Field(..., gt=0, description="Maximum allowed minutes")
    tokens: int = Field(..., ge=0, description="Used tokens")
    max_tokens: int = Field(..., gt=0, description="Maximum allowed tokens")


class Skill(BaseModel):
    """User skill model."""
    id: str = Field(..., description="Skill unique identifier")
    name: str = Field(..., min_length=1, description="Skill name")
    score: int = Field(..., ge=0, le=100, description="Skill score out of 100")
    description: Optional[str] = Field(None, description="Skill description")


class UserBase(BaseModel):
    """Base user model with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    role: UserRole = Field(default=UserRole.MEMBER, description="User role")
    plan: Optional[UserPlan] = Field(default=UserPlan.FREE, description="User subscription plan")
    status: Optional[UserStatus] = Field(default=UserStatus.ACTIVE, description="User status")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    job_description: Optional[str] = Field(None, description="User job description")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    plan: Optional[UserPlan] = None
    status: Optional[UserStatus] = None
    avatar_url: Optional[str] = None
    job_description: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: str = Field(..., description="User unique identifier")
    usage: Optional[UserUsage] = Field(None, description="User usage statistics")
    skills: Optional[List[Skill]] = Field(default_factory=list, description="User skills")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: List[UserResponse]
    total: int = Field(..., ge=0, description="Total number of users")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
