#!/usr/bin/env python3
"""
Test WebSocket subscriber endpoint
"""
import asyncio
import websockets
import json
import sys

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NTAzNTU0LCJpYXQiOjE3NTY0MTcxNTQsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.F7MLhv2j4J3po8LGBL-8mIFicOBvhudMZMah0jfdJeE"

async def test_subscriber():
    """Test subscriber WebSocket"""
    meeting_id = "test-001"
    url = f"ws://localhost:8000/api/v1/ws/meetings/{meeting_id}?token={TOKEN}"
    
    try:
        print(f"🔗 Connecting to subscriber WebSocket: {meeting_id}")
        async with websockets.connect(url) as ws:
            print("✅ Connected to subscriber WebSocket!")
            
            # Test ping/pong
            await ws.send("ping")
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"📨 Ping response: {response}")
            
            # Listen for messages (timeout after 10 seconds)
            try:
                while True:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    print(f"📨 Received: {message}")
            except asyncio.TimeoutError:
                print("⏰ No more messages (timeout)")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_subscriber())
    sys.exit(0 if success else 1)
