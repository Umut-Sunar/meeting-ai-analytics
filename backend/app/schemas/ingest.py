"""
Pydantic schemas for file ingest and upload operations.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class IngestStartRequest(BaseModel):
    """Request to start a multipart upload."""
    
    file_type: str = Field(..., description="Type of file (audio_raw, audio_mp3, document, export)")
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., gt=0, description="Total file size in bytes")
    content_type: str = Field(default="application/octet-stream", description="MIME type")
    part_count: int = Field(..., gt=0, le=10000, description="Number of parts for multipart upload")
    
    @validator('file_type')
    def validate_file_type(cls, v):
        allowed_types = ['audio_raw', 'audio_mp3', 'document', 'export']
        if v not in allowed_types:
            raise ValueError(f'file_type must be one of: {allowed_types}')
        return v
    
    @validator('part_count')
    def validate_part_count(cls, v, values):
        if 'file_size' in values:
            # Each part should be at least 5MB except the last one
            min_part_size = 5 * 1024 * 1024  # 5MB
            if values['file_size'] > min_part_size * v:
                raise ValueError('Part count too high for file size')
        return v


class PresignedUrlInfo(BaseModel):
    """Information about a presigned upload URL."""
    
    part_number: int = Field(..., description="Part number (1-based)")
    upload_url: str = Field(..., description="Presigned upload URL")
    expires_at: datetime = Field(..., description="URL expiration time")


class IngestStartResponse(BaseModel):
    """Response from starting a multipart upload."""
    
    upload_id: str = Field(..., description="Multipart upload ID")
    object_key: str = Field(..., description="S3 object key")
    bucket_name: str = Field(..., description="S3 bucket name")
    upload_urls: List[PresignedUrlInfo] = Field(..., description="Presigned upload URLs for each part")
    expires_at: datetime = Field(..., description="Upload session expiration")


class UploadedPart(BaseModel):
    """Information about an uploaded part."""
    
    part_number: int = Field(..., description="Part number (1-based)")
    etag: str = Field(..., description="ETag returned from upload")
    size: Optional[int] = Field(None, description="Part size in bytes")


class IngestCompleteRequest(BaseModel):
    """Request to complete a multipart upload."""
    
    upload_id: str = Field(..., description="Multipart upload ID")
    object_key: str = Field(..., description="S3 object key")
    parts: List[UploadedPart] = Field(..., description="List of uploaded parts")
    
    @validator('parts')
    def validate_parts(cls, v):
        if not v:
            raise ValueError('At least one part is required')
        
        # Check for duplicate part numbers
        part_numbers = [part.part_number for part in v]
        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError('Duplicate part numbers found')
        
        # Check part numbers are sequential starting from 1
        sorted_parts = sorted(part_numbers)
        if sorted_parts != list(range(1, len(sorted_parts) + 1)):
            raise ValueError('Part numbers must be sequential starting from 1')
        
        return v


class IngestCompleteResponse(BaseModel):
    """Response from completing a multipart upload."""
    
    audio_blob_id: UUID = Field(..., description="Created audio blob ID")
    object_key: str = Field(..., description="S3 object key")
    bucket_name: str = Field(..., description="S3 bucket name")
    file_size: int = Field(..., description="Total file size in bytes")
    etag: str = Field(..., description="Final ETag")
    completed_at: datetime = Field(..., description="Upload completion time")


class IngestStatusResponse(BaseModel):
    """Response for upload status check."""
    
    upload_id: str = Field(..., description="Multipart upload ID")
    object_key: str = Field(..., description="S3 object key")
    status: str = Field(..., description="Upload status (in_progress, completed, failed, aborted)")
    parts_uploaded: int = Field(..., description="Number of parts uploaded")
    total_parts: int = Field(..., description="Total number of parts")
    created_at: datetime = Field(..., description="Upload start time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class IngestErrorResponse(BaseModel):
    """Error response for ingest operations."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    upload_id: Optional[str] = Field(None, description="Upload ID if applicable")
    details: Optional[Dict] = Field(None, description="Additional error details")
