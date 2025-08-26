"""
Meeting management endpoints for CRUD operations and filtering.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, status, Depends
from datetime import datetime

from app.schemas.meetings import (
    MeetingResponse,
    MeetingCreate,
    MeetingUpdate,
    MeetingListResponse,
    MeetingFilters
)

router = APIRouter()

# Mock data for development - will be replaced with database operations
MOCK_MEETINGS = [
    {
        "id": "m1",
        "title": "Q3 Product Strategy Sync",
        "date": "2024-07-22T10:00:00Z",
        "duration": 45,
        "participants": [],
        "summaries": {},
        "transcript": [],
        "analytics": None,
        "created_at": "2024-07-22T09:00:00Z",
        "updated_at": None,
    },
    {
        "id": "m2", 
        "title": "Acme Corp. Client Pitch",
        "date": "2024-07-21T14:00:00Z",
        "duration": 62,
        "participants": [],
        "summaries": {},
        "transcript": [],
        "analytics": None,
        "created_at": "2024-07-21T13:00:00Z",
        "updated_at": None,
    },
]


@router.get(
    "/meetings",
    response_model=MeetingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Meetings",
    description="Get a paginated list of meetings with optional filtering"
)
async def get_meetings(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    participant_id: Optional[str] = Query(None, description="Filter by participant ID"),
    date_from: Optional[datetime] = Query(None, description="Filter meetings from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter meetings until this date"),
    min_duration: Optional[int] = Query(None, gt=0, description="Minimum duration in minutes"),
    max_duration: Optional[int] = Query(None, gt=0, description="Maximum duration in minutes"),
) -> MeetingListResponse:
    """
    Retrieve a paginated list of meetings with optional filtering.
    
    Args:
        page: Page number (1-based)
        per_page: Number of items per page (1-100)
        title: Filter by title (partial match)
        participant_id: Filter by participant ID
        date_from: Filter meetings from this date
        date_to: Filter meetings until this date
        min_duration: Minimum duration in minutes
        max_duration: Maximum duration in minutes
    
    Returns:
        MeetingListResponse: Paginated list of meetings
    """
    # TODO: Replace with actual database queries
    filtered_meetings = MOCK_MEETINGS.copy()
    
    # Apply filters
    if title:
        filtered_meetings = [m for m in filtered_meetings if title.lower() in m["title"].lower()]
    
    if date_from:
        filtered_meetings = [m for m in filtered_meetings if datetime.fromisoformat(m["date"].replace('Z', '+00:00')) >= date_from]
    
    if date_to:
        filtered_meetings = [m for m in filtered_meetings if datetime.fromisoformat(m["date"].replace('Z', '+00:00')) <= date_to]
        
    if min_duration:
        filtered_meetings = [m for m in filtered_meetings if m["duration"] >= min_duration]
        
    if max_duration:
        filtered_meetings = [m for m in filtered_meetings if m["duration"] <= max_duration]
    
    # Pagination
    total = len(filtered_meetings)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_meetings = filtered_meetings[start_idx:end_idx]
    
    return MeetingListResponse(
        meetings=[MeetingResponse(**meeting) for meeting in paginated_meetings],
        total=total,
        page=page,
        per_page=per_page,
        has_next=end_idx < total,
        has_prev=page > 1
    )


@router.get(
    "/meetings/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Meeting",
    description="Get a specific meeting by ID"
)
async def get_meeting(meeting_id: str) -> MeetingResponse:
    """
    Retrieve a specific meeting by its ID.
    
    Args:
        meeting_id: Meeting unique identifier
        
    Returns:
        MeetingResponse: Meeting details
        
    Raises:
        HTTPException: If meeting not found
    """
    # TODO: Replace with actual database query
    meeting = next((m for m in MOCK_MEETINGS if m["id"] == meeting_id), None)
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {meeting_id} not found"
        )
    
    return MeetingResponse(**meeting)


@router.post(
    "/meetings",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Meeting",
    description="Create a new meeting"
)
async def create_meeting(meeting_data: MeetingCreate) -> MeetingResponse:
    """
    Create a new meeting.
    
    Args:
        meeting_data: Meeting creation data
        
    Returns:
        MeetingResponse: Created meeting details
    """
    # TODO: Replace with actual database creation
    new_meeting = {
        "id": f"m{len(MOCK_MEETINGS) + 1}",
        "title": meeting_data.title,
        "date": meeting_data.date.isoformat(),
        "duration": meeting_data.duration,
        "participants": [],  # Will be populated with actual user data
        "summaries": {},
        "transcript": meeting_data.transcript or [],
        "analytics": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": None,
    }
    
    MOCK_MEETINGS.append(new_meeting)
    
    return MeetingResponse(**new_meeting)


@router.put(
    "/meetings/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Meeting",
    description="Update an existing meeting"
)
async def update_meeting(meeting_id: str, meeting_data: MeetingUpdate) -> MeetingResponse:
    """
    Update an existing meeting.
    
    Args:
        meeting_id: Meeting unique identifier
        meeting_data: Meeting update data
        
    Returns:
        MeetingResponse: Updated meeting details
        
    Raises:
        HTTPException: If meeting not found
    """
    # TODO: Replace with actual database update
    meeting_idx = next((i for i, m in enumerate(MOCK_MEETINGS) if m["id"] == meeting_id), None)
    
    if meeting_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {meeting_id} not found"
        )
    
    meeting = MOCK_MEETINGS[meeting_idx]
    
    # Update fields if provided
    if meeting_data.title is not None:
        meeting["title"] = meeting_data.title
    if meeting_data.date is not None:
        meeting["date"] = meeting_data.date.isoformat()
    if meeting_data.duration is not None:
        meeting["duration"] = meeting_data.duration
    if meeting_data.transcript is not None:
        meeting["transcript"] = meeting_data.transcript
    
    meeting["updated_at"] = datetime.now().isoformat()
    
    return MeetingResponse(**meeting)


@router.delete(
    "/meetings/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Meeting",
    description="Delete a meeting"
)
async def delete_meeting(meeting_id: str) -> None:
    """
    Delete a meeting.
    
    Args:
        meeting_id: Meeting unique identifier
        
    Raises:
        HTTPException: If meeting not found
    """
    # TODO: Replace with actual database deletion
    meeting_idx = next((i for i, m in enumerate(MOCK_MEETINGS) if m["id"] == meeting_id), None)
    
    if meeting_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {meeting_id} not found"
        )
    
    MOCK_MEETINGS.pop(meeting_idx)
