#!/usr/bin/env python3
"""
Test dual-source WebSocket connections.
"""

import asyncio
import json
import websockets
import jwt
import time
from datetime import datetime


def generate_test_token():
    """Generate test JWT token."""
    secret_key = "your-secret-key-here-change-in-production"  # From .env
    payload = {
        "user_id": "test-user-001",
        "tenant_id": "test-tenant-001", 
        "email": "test@example.com",
        "role": "user",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "aud": "meetings",
        "iss": "our-app"
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


async def test_dual_source_connection():
    """Test dual-source WebSocket connections."""
    
    token = generate_test_token()
    meeting_id = "test-meeting-dual"
    base_url = "ws://localhost:8000/api/v1/ws/ingest/meetings"
    
    print("🚀 Testing dual-source WebSocket connections...")
    
    try:
        # Test 1: Connect with mic source
        mic_url = f"{base_url}/{meeting_id}?source=mic"
        print(f"📥 Connecting to: {mic_url}")
        
        async with websockets.connect(
            mic_url,
            additional_headers={"Authorization": f"Bearer {token}"}
        ) as mic_ws:
            print("✅ MIC WebSocket connected")
            
            # Send handshake for mic
            mic_handshake = {
                "type": "handshake",
                "source": "mic",
                "sample_rate": 48000,
                "channels": 1,
                "language": "tr",
                "ai_mode": "standard",
                "device_id": "test-device-mic"
            }
            await mic_ws.send(json.dumps(mic_handshake))
            print("📤 MIC handshake sent")
            
            # Receive response
            response = await mic_ws.recv()
            print(f"📨 MIC response: {response}")
            
            # Test 2: Connect with sys source (in parallel)
            sys_url = f"{base_url}/{meeting_id}?source=sys"
            print(f"📥 Connecting to: {sys_url}")
            
            async with websockets.connect(
                sys_url,
                additional_headers={"Authorization": f"Bearer {token}"}
            ) as sys_ws:
                print("✅ SYS WebSocket connected")
                
                # Send handshake for sys
                sys_handshake = {
                    "type": "handshake",
                    "source": "system",  # Backend expects "system" but maps to "sys"
                    "sample_rate": 48000,
                    "channels": 1,
                    "language": "tr",
                    "ai_mode": "standard",
                    "device_id": "test-device-sys"
                }
                await sys_ws.send(json.dumps(sys_handshake))
                print("📤 SYS handshake sent")
                
                # Receive response
                response = await sys_ws.recv()
                print(f"📨 SYS response: {response}")
                
                print("🎉 Both connections established successfully!")
                
                # Test 3: Try duplicate mic connection (should fail)
                print("🔄 Testing duplicate mic connection...")
                try:
                    async with websockets.connect(
                        mic_url,
                        additional_headers={"Authorization": f"Bearer {token}"}
                    ) as duplicate_ws:
                        await duplicate_ws.send(json.dumps(mic_handshake))
                        response = await duplicate_ws.recv()
                        print(f"❌ Duplicate connection unexpectedly succeeded: {response}")
                except Exception as e:
                    print(f"✅ Duplicate connection correctly rejected: {e}")
                
                # Keep connections alive for a moment
                await asyncio.sleep(2)
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


async def test_connection_stats():
    """Test connection stats endpoint."""
    import aiohttp
    
    meeting_id = "test-meeting-dual"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:8000/api/v1/ws/meetings/{meeting_id}/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    print(f"📊 Meeting stats: {json.dumps(stats, indent=2)}")
                else:
                    print(f"❌ Stats request failed: {response.status}")
    except Exception as e:
        print(f"❌ Stats test failed: {e}")


if __name__ == "__main__":
    print("🧪 Dual-Source WebSocket Test")
    print("=" * 50)
    
    asyncio.run(test_dual_source_connection())
    print("\n📊 Testing connection stats...")
    asyncio.run(test_connection_stats())
    
    print("\n✅ All tests completed!")
