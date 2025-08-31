"""
Health check endpoints for monitoring and status verification.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.services.pubsub.redis_bus import redis_bus
from app import APP_VERSION

# Storage service import guarded for optional use
try:
    from app.services.storage import storage_service
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model for k8s/ecs probes."""
    redis: str
    storage: str
    version: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Simple health check endpoint for k8s/ecs probes. Returns redis, storage status and version."
)
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint optimized for k8s/ecs probes.
    
    Returns:
        HealthResponse: Redis status (ok|down), storage status (ok|down), and version
    """
    # Check Redis connection
    redis_status = "down"
    if redis_bus.redis:
        try:
            await redis_bus.redis.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "down"
    
    # Check Storage connection  
    storage_status = "down"
    if STORAGE_AVAILABLE and storage_service:
        try:
            # Lightweight check - list buckets
            buckets = await storage_service.list_buckets()
            storage_status = "ok" if buckets is not None else "down"
        except Exception:
            storage_status = "down"
    else:
        # If storage is not available/configured, consider it as "down"
        storage_status = "down"
    
    return HealthResponse(
        redis=redis_status,
        storage=storage_status,
        version=APP_VERSION
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Detailed health check with timestamp and service breakdown"
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check endpoint with full service breakdown.
    
    Returns:
        DetailedHealthResponse: Complete health status with timestamp and service states
    """
    # Check Redis connection
    redis_status = "unhealthy"
    if redis_bus.redis:
        try:
            await redis_bus.redis.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "unhealthy"
    
    # Check Storage connection
    storage_status = "unhealthy"
    if STORAGE_AVAILABLE and storage_service:
        try:
            buckets = await storage_service.list_buckets()
            if buckets:
                storage_status = "healthy"
        except Exception:
            storage_status = "unhealthy"
    else:
        storage_status = "unavailable"
    
    services = {
        "database": "healthy",  # Will be implemented with actual DB check
        "redis": redis_status,
        "storage": storage_status,
    }
    
    # Overall status - healthy if all critical services are up
    overall_status = "healthy" if redis_status in ["healthy"] and storage_status in ["healthy", "unavailable"] else "unhealthy"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        version=APP_VERSION,
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
    return {"message": "pong", "timestamp": datetime.now(), "version": APP_VERSION}