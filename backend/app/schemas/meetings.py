"""
Meeting-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .users import UserResponse


class TranscriptSegment(BaseModel):
    """Individual transcript segment."""
    speaker: str = Field(..., description="Speaker identifier")
    speaker_label: str = Field(..., description="Speaker display name")
    timestamp: int = Field(..., ge=0, description="Timestamp in seconds")
    text: str = Field(..., description="Spoken text")


class AIPromptType(str, Enum):
    """AI prompt type enumeration."""
    DEFAULT = "default"
    CUSTOM = "custom"


class PromptTag(str, Enum):
    """Prompt tag enumeration."""
    MEETING_SUMMARY = "Meeting Summary"
    MEETING_ASSISTANT = "Meeting Assistant"


class AIPrompt(BaseModel):
    """AI prompt model."""
    id: str = Field(..., description="Prompt unique identifier")
    name: str = Field(..., min_length=1, description="Prompt name")
    text: str = Field(..., min_length=1, description="Prompt text")
    type: AIPromptType = Field(..., description="Prompt type")
    tags: Optional[List[PromptTag]] = Field(default_factory=list, description="Prompt tags")


class MeetingSummary(BaseModel):
    """Meeting summary for specific prompt."""
    overview: List[str] = Field(default_factory=list, description="Meeting overview points")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    key_topics: List[str] = Field(default_factory=list, description="Key discussion topics")


class TalkRatioItem(BaseModel):
    """Talk ratio statistics for participant."""
    name: str = Field(..., description="Participant name")
    value: int = Field(..., ge=0, le=100, description="Talk percentage")
    color: str = Field(..., description="Display color")


class SentimentPoint(BaseModel):
    """Sentiment analysis point."""
    time: int = Field(..., ge=0, description="Time in minutes")
    value: float = Field(..., ge=-1, le=1, description="Sentiment value (-1 to 1)")


class MeetingAnalytics(BaseModel):
    """Meeting analytics data."""
    talk_ratio: List[TalkRatioItem] = Field(default_factory=list, description="Talk time distribution")
    sentiment: List[SentimentPoint] = Field(default_factory=list, description="Sentiment over time")


class MeetingBase(BaseModel):
    """Base meeting model with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    date: datetime = Field(..., description="Meeting date and time")
    duration: int = Field(..., gt=0, description="Meeting duration in minutes")


class MeetingCreate(MeetingBase):
    """Schema for creating a new meeting."""
    participant_ids: List[str] = Field(..., min_items=1, description="List of participant user IDs")
    transcript: Optional[List[TranscriptSegment]] = Field(default_factory=list, description="Meeting transcript")


class MeetingUpdate(BaseModel):
    """Schema for updating meeting information."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    date: Optional[datetime] = None
    duration: Optional[int] = Field(None, gt=0)
    participant_ids: Optional[List[str]] = None
    transcript: Optional[List[TranscriptSegment]] = None


class MeetingResponse(MeetingBase):
    """Schema for meeting response."""
    id: str = Field(..., description="Meeting unique identifier")
    participants: List[UserResponse] = Field(default_factory=list, description="Meeting participants")
    summaries: Dict[str, MeetingSummary] = Field(default_factory=dict, description="AI-generated summaries by prompt ID")
    transcript: List[TranscriptSegment] = Field(default_factory=list, description="Meeting transcript")
    analytics: Optional[MeetingAnalytics] = Field(None, description="Meeting analytics data")
    created_at: datetime = Field(..., description="Meeting creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list response."""
    meetings: List[MeetingResponse]
    total: int = Field(..., ge=0, description="Total number of meetings")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class MeetingFilters(BaseModel):
    """Schema for meeting filtering parameters."""
    title: Optional[str] = Field(None, description="Filter by title (partial match)")
    participant_id: Optional[str] = Field(None, description="Filter by participant ID")
    date_from: Optional[datetime] = Field(None, description="Filter meetings from this date")
    date_to: Optional[datetime] = Field(None, description="Filter meetings until this date")
    min_duration: Optional[int] = Field(None, gt=0, description="Minimum duration in minutes")
    max_duration: Optional[int] = Field(None, gt=0, description="Maximum duration in minutes")
