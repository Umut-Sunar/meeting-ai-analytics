"""
Health check endpoints for monitoring and status verification.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.services.pubsub.redis_bus import redis_bus

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of the API and its dependencies"
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns the current status of the API.
    
    Returns:
        HealthResponse: Current health status with timestamp and service states
    """
    # Check Redis connection
    redis_status = "unhealthy"
    if redis_bus.redis:
        try:
            await redis_bus.redis.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "unhealthy"
    
    services = {
        "database": "healthy",  # Will be implemented with actual DB check
        "redis": redis_status,
        "storage": "healthy",   # Will be implemented with actual MinIO check
    }
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="0.1.0",
        services=services
    )


@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    summary="Simple Ping",
    description="Simple ping endpoint for basic availability check"
)
async def ping() -> Dict[str, Any]:
    """
    Simple ping endpoint for basic availability testing.
    
    Returns:
        Dict containing pong response
    """
    return {"message": "pong", "timestamp": datetime.now()}
