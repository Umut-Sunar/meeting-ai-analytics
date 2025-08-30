"""
Meeting AI Analytics Backend API

FastAPI application for meeting analysis and management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, meetings, ingest, ws
# Storage service import guarded for optional use
try:
    from app.services.storage import storage_service
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
from app.services.ws.connection import ws_manager
from app.services.pubsub.redis_bus import redis_bus

# Create FastAPI app
app = FastAPI(
    title="Meeting AI Analytics API",
    description="Backend API for AI-powered meeting analysis and management system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(meetings.router, prefix="/api/v1", tags=["meetings"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(ws.router, prefix="/api/v1", tags=["websockets"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Initialize MinIO buckets (if available)
    if STORAGE_AVAILABLE:
        try:
            await storage_service.initialize_buckets()
            print("✅ Storage service initialized")
        except Exception as e:
            print(f"⚠️ Storage service failed: {e}")
    else:
        print("⚠️ Storage service not available (skipped)")
    
    # Initialize Redis connection with explicit fail-fast behavior
    try:
        await redis_bus.connect()
        if redis_bus.redis:
            print("✅ Redis bus initialized")
        else:
            print("⚠️ Redis bus initialized (no-op mode - streaming disabled)")
    except SystemExit:
        # Redis connection was required but failed - stop startup
        print("🚨 Application startup failed due to required Redis connection")
        raise
    except Exception as e:
        # Unexpected error during Redis initialization
        print(f"❌ Unexpected Redis initialization error: {e}")
        raise
    
    # WebSocket manager doesn't need explicit start
    print("✅ WebSocket manager ready")
    print("✅ Backend startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    try:
        # WebSocket manager cleanup is automatic
        print("✅ WebSocket manager cleaned up")
        
        # Disconnect Redis
        await redis_bus.disconnect()
        print("✅ Redis bus disconnected")
        
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Meeting AI Analytics API",
        "version": "0.1.0",
        "status": "running",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
