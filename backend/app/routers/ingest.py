"""
File ingest endpoints for multipart uploads to MinIO/S3.
Handles audio files, documents, and exports with presigned URLs.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.connection import get_db
from app.models.meetings import Meeting
from app.models.enums import StreamSource, Codec
from app.schemas.ingest import (
    IngestStartRequest,
    IngestStartResponse,
    IngestCompleteRequest,
    IngestCompleteResponse,
    IngestStatusResponse,
    IngestErrorResponse
)
from app.services.storage import storage_service

router = APIRouter()
settings = get_settings()

# Mapping file types to buckets
FILE_TYPE_TO_BUCKET = {
    "audio_raw": storage_service.BUCKETS["audio_raw"],
    "audio_mp3": storage_service.BUCKETS["audio_mp3"],
    "document": storage_service.BUCKETS["documents"],
    "export": storage_service.BUCKETS["exports"]
}

# In-memory upload tracking (in production, use Redis)
active_uploads: Dict[str, Dict] = {}


@router.post(
    "/meetings/{meeting_id}/ingest/start",
    response_model=IngestStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Multipart Upload",
    description="Initialize a multipart upload and get presigned URLs for file parts"
)
async def start_ingest(
    meeting_id: str = Path(..., description="Meeting ID"),
    request: IngestStartRequest = ...,
    db: AsyncSession = Depends(get_db)
) -> IngestStartResponse:
    """
    Start a multipart upload for a meeting file.
    
    Args:
        meeting_id: Meeting unique identifier
        request: Upload initialization request
        db: Database session
        
    Returns:
        IngestStartResponse: Upload session with presigned URLs
        
    Raises:
        HTTPException: If meeting not found or upload initialization fails
    """
    try:
        # Verify meeting exists (in production, check user permissions)
        # For now, we'll skip the DB check and use mock validation
        if not meeting_id or len(meeting_id) < 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting with ID {meeting_id} not found"
            )
        
        # Get bucket name for file type
        bucket_name = FILE_TYPE_TO_BUCKET.get(request.file_type)
        if not bucket_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type: {request.file_type}"
            )
        
        # Generate unique object key
        file_extension = request.file_name.split('.')[-1] if '.' in request.file_name else 'bin'
        object_key = storage_service.generate_object_key(
            meeting_id=meeting_id,
            file_type=request.file_type,
            file_extension=file_extension
        )
        
        # Initialize multipart upload
        upload_id = await storage_service.create_multipart_upload(
            bucket_name=bucket_name,
            object_key=object_key,
            content_type=request.content_type
        )
        
        # Generate presigned URLs for all parts
        upload_urls = await storage_service.generate_presigned_upload_urls(
            bucket_name=bucket_name,
            object_key=object_key,
            upload_id=upload_id,
            part_count=request.part_count,
            expiration=settings.PRESIGNED_URL_EXPIRE_SECONDS
        )
        
        # Track upload session
        expires_at = datetime.utcnow() + timedelta(seconds=settings.PRESIGNED_URL_EXPIRE_SECONDS)
        active_uploads[upload_id] = {
            "meeting_id": meeting_id,
            "object_key": object_key,
            "bucket_name": bucket_name,
            "file_name": request.file_name,
            "file_size": request.file_size,
            "file_type": request.file_type,
            "content_type": request.content_type,
            "total_parts": request.part_count,
            "parts_uploaded": 0,
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        
        return IngestStartResponse(
            upload_id=upload_id,
            object_key=object_key,
            bucket_name=bucket_name,
            upload_urls=upload_urls,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting ingest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize upload"
        )


@router.post(
    "/meetings/{meeting_id}/ingest/complete",
    response_model=IngestCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Multipart Upload",
    description="Complete a multipart upload and create audio_blob record"
)
async def complete_ingest(
    meeting_id: str = Path(..., description="Meeting ID"),
    request: IngestCompleteRequest = ...,
    db: AsyncSession = Depends(get_db)
) -> IngestCompleteResponse:
    """
    Complete a multipart upload and create database records.
    
    Args:
        meeting_id: Meeting unique identifier
        request: Upload completion request
        db: Database session
        
    Returns:
        IngestCompleteResponse: Completed upload information
        
    Raises:
        HTTPException: If upload not found or completion fails
    """
    try:
        # Get upload session
        upload_session = active_uploads.get(request.upload_id)
        if not upload_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {request.upload_id} not found"
            )
        
        # Verify meeting ID matches
        if upload_session["meeting_id"] != meeting_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting ID mismatch"
            )
        
        # Check if upload expired
        if datetime.utcnow() > upload_session["expires_at"]:
            # Clean up expired upload
            await storage_service.abort_multipart_upload(
                bucket_name=upload_session["bucket_name"],
                object_key=upload_session["object_key"],
                upload_id=request.upload_id
            )
            del active_uploads[request.upload_id]
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Upload session expired"
            )
        
        # Complete multipart upload
        completion_result = await storage_service.complete_multipart_upload(
            bucket_name=upload_session["bucket_name"],
            object_key=upload_session["object_key"],
            upload_id=request.upload_id,
            parts=[part.dict() for part in request.parts]
        )
        
        # Get final object info
        object_info = await storage_service.get_object_info(
            bucket_name=upload_session["bucket_name"],
            object_key=upload_session["object_key"]
        )
        
        # Create audio_blob record (for now, we'll generate a UUID)
        # In production, this would create a proper database record
        audio_blob_id = uuid.uuid4()
        
        # TODO: Create actual database record
        # audio_blob = AudioBlob(
        #     id=audio_blob_id,
        #     meeting_id=meeting_id,
        #     source=StreamSource.MICROPHONE,  # or determine from file_type
        #     s3_key=upload_session["object_key"],
        #     duration_ms=0,  # Will be determined by audio processing
        #     size_bytes=object_info["size"],
        #     part_no=1,  # For single file uploads
        #     checksum=object_info["etag"],
        #     created_at=datetime.utcnow()
        # )
        # db.add(audio_blob)
        # await db.commit()
        
        # Update upload session
        upload_session["status"] = "completed"
        upload_session["parts_uploaded"] = len(request.parts)
        upload_session["completed_at"] = datetime.utcnow()
        
        # Clean up session after some time (in production, use background task)
        # For now, keep it for status checks
        
        return IngestCompleteResponse(
            audio_blob_id=audio_blob_id,
            object_key=upload_session["object_key"],
            bucket_name=upload_session["bucket_name"],
            file_size=object_info["size"],
            etag=completion_result["etag"],
            completed_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error completing ingest: {e}")
        # Try to abort the upload on error
        try:
            if request.upload_id in active_uploads:
                session = active_uploads[request.upload_id]
                await storage_service.abort_multipart_upload(
                    bucket_name=session["bucket_name"],
                    object_key=session["object_key"],
                    upload_id=request.upload_id
                )
                del active_uploads[request.upload_id]
        except:
            pass  # Best effort cleanup
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete upload"
        )


@router.get(
    "/meetings/{meeting_id}/ingest/{upload_id}/status",
    response_model=IngestStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Upload Status",
    description="Check the status of a multipart upload"
)
async def get_ingest_status(
    meeting_id: str = Path(..., description="Meeting ID"),
    upload_id: str = Path(..., description="Upload ID")
) -> IngestStatusResponse:
    """
    Get the status of a multipart upload.
    
    Args:
        meeting_id: Meeting unique identifier
        upload_id: Upload session ID
        
    Returns:
        IngestStatusResponse: Upload status information
        
    Raises:
        HTTPException: If upload session not found
    """
    upload_session = active_uploads.get(upload_id)
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {upload_id} not found"
        )
    
    if upload_session["meeting_id"] != meeting_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting ID mismatch"
        )
    
    return IngestStatusResponse(
        upload_id=upload_id,
        object_key=upload_session["object_key"],
        status=upload_session["status"],
        parts_uploaded=upload_session["parts_uploaded"],
        total_parts=upload_session["total_parts"],
        created_at=upload_session["created_at"],
        updated_at=upload_session.get("updated_at")
    )


@router.delete(
    "/meetings/{meeting_id}/ingest/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Abort Upload",
    description="Abort a multipart upload and clean up parts"
)
async def abort_ingest(
    meeting_id: str = Path(..., description="Meeting ID"),
    upload_id: str = Path(..., description="Upload ID")
) -> None:
    """
    Abort a multipart upload and clean up uploaded parts.
    
    Args:
        meeting_id: Meeting unique identifier
        upload_id: Upload session ID
        
    Raises:
        HTTPException: If upload session not found
    """
    upload_session = active_uploads.get(upload_id)
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session {upload_id} not found"
        )
    
    if upload_session["meeting_id"] != meeting_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting ID mismatch"
        )
    
    try:
        # Abort multipart upload
        await storage_service.abort_multipart_upload(
            bucket_name=upload_session["bucket_name"],
            object_key=upload_session["object_key"],
            upload_id=upload_id
        )
        
        # Update session status
        upload_session["status"] = "aborted"
        upload_session["updated_at"] = datetime.utcnow()
        
        # Remove from active uploads
        del active_uploads[upload_id]
        
    except Exception as e:
        print(f"❌ Error aborting ingest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort upload"
        )
