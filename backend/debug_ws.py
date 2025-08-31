#!/usr/bin/env python3
"""
Debug WebSocket endpoint issues
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket

# Test if we can create a simple WebSocket endpoint
app = FastAPI()

@app.websocket("/test-ws")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello WebSocket!")
    await websocket.close()

# Test the main app
try:
    from app.main import app as main_app
    print("✅ Main app import successful")
    
    # Test if we can access the WebSocket route
    from app.routers.ws import router
    print("✅ WebSocket router import successful")
    
    # Test if we can import the ingest handler
    from app.websocket.ingest import handle_websocket_ingest
    print("✅ Ingest handler import successful")
    
    # Test WebSocket endpoint registration
    routes = [route for route in main_app.routes if hasattr(route, 'path')]
    ws_routes = [route for route in routes if hasattr(route, 'path') and 'ws' in route.path]
    
    print(f"📋 Found {len(ws_routes)} WebSocket routes:")
    for route in ws_routes:
        print(f"   - {route.path}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
