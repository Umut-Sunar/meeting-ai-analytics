#!/usr/bin/env python3
"""
Test script for WebSocket ingest handshake protocol.
"""

import asyncio
import json
import websockets
import sys

async def test_handshake_protocol():
    """Test the new handshake protocol."""
    
    # Use provided JWT token
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NjgzMzUzLCJpYXQiOjE3NTY1OTY5NTMsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.jVeHk5a52u_zogEg-nQuRkYNACdln0ytOoO5BIACDgMRBlaQq82bvXEl_Ua3P2wqp0OOe_de9-5oOznlaO6C-_8P7RofhlLCYiOnjWDnOoY0EMBtr8o1MotawacYcNc2Vkyd7t_7kqKGW_oF9gGe6I_RQ-Tq6ummOnJ9WLeuOQhnH6EesE6PVxTdMdw2P4XahcSTB3BzDYeedPrx3U_BUFfzDPiqv4QQlVJNCrlHM0TyfjrQm9EcjLRDgARM2jlz2Ig9b7jiwWdP-SI9q4IsxhliS6ZxGDETypEvzFNSBXRC17Iz8nd-pgpTwHhdlnH9JiH8hIZ4hgT-FrInK0r7VQ"
    
    uri = f"ws://localhost:8000/ws/ingest/meetings/m1?source=mic&token={jwt_token}"
    
    print(f"🔌 Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Test 1: Send valid handshake
            handshake = {
                "type": "handshake",
                "device_id": "test-device-001",
                "source": "mic",
                "sample_rate": 16000,
                "channels": 1
            }
            
            print(f"📤 Sending handshake: {handshake}")
            await websocket.send(json.dumps(handshake))
            
            # Wait for handshake-ack
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            ack = json.loads(response)
            if ack.get("type") == "handshake-ack" and ack.get("ok"):
                print("✅ Handshake successful!")
            else:
                print(f"❌ Unexpected response: {ack}")
                
            # Keep connection alive for a moment
            await asyncio.sleep(2)
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e.code} - {e.reason}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_invalid_handshake():
    """Test invalid handshake scenarios."""
    
    # Use provided JWT token
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NjgzMzUzLCJpYXQiOjE3NTY1OTY5NTMsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.jVeHk5a52u_zogEg-nQuRkYNACdln0ytOoO5BIACDgMRBlaQq82bvXEl_Ua3P2wqp0OOe_de9-5oOznlaO6C-_8P7RofhlLCYiOnjWDnOoY0EMBtr8o1MotawacYcNc2Vkyd7t_7kqKGW_oF9gGe6I_RQ-Tq6ummOnJ9WLeuOQhnH6EesE6PVxTdMdw2P4XahcSTB3BzDYeedPrx3U_BUFfzDPiqv4QQlVJNCrlHM0TyfjrQm9EcjLRDgARM2jlz2Ig9b7jiwWdP-SI9q4IsxhliS6ZxGDETypEvzFNSBXRC17Iz8nd-pgpTwHhdlnH9JiH8hIZ4hgT-FrInK0r7VQ"
    
    uri = f"ws://localhost:8000/ws/ingest/meetings/m1?source=sys&token={jwt_token}"
    
    print(f"\n🔌 Testing invalid handshake on {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Test: Send invalid first frame
            invalid_msg = {
                "type": "audio_data",
                "data": "not-a-handshake"
            }
            
            print(f"📤 Sending invalid first frame: {invalid_msg}")
            await websocket.send(json.dumps(invalid_msg))
            
            # Should get connection closed
            try:
                response = await websocket.recv()
                print(f"📥 Unexpected response: {response}")
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"✅ Connection properly closed: {e.code} - {e.reason}")
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✅ Connection closed as expected: {e.code} - {e.reason}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_handshake_timeout():
    """Test handshake timeout."""
    
    # Use provided JWT token
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NjgzMzUzLCJpYXQiOjE3NTY1OTY5NTMsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.jVeHk5a52u_zogEg-nQuRkYNACdln0ytOoO5BIACDgMRBlaQq82bvXEl_Ua3P2wqp0OOe_de9-5oOznlaO6C-_8P7RofhlLCYiOnjWDnOoY0EMBtr8o1MotawacYcNc2Vkyd7t_7kqKGW_oF9gGe6I_RQ-Tq6ummOnJ9WLeuOQhnH6EesE6PVxTdMdw2P4XahcSTB3BzDYeedPrx3U_BUFfzDPiqv4QQlVJNCrlHM0TyfjrQm9EcjLRDgARM2jlz2Ig9b7jiwWdP-SI9q4IsxhliS6ZxGDETypEvzFNSBXRC17Iz8nd-pgpTwHhdlnH9JiH8hIZ4hgT-FrInK0r7VQ"
    
    uri = f"ws://localhost:8000/ws/ingest/meetings/m2?source=mic&token={jwt_token}"
    
    print(f"\n🔌 Testing handshake timeout on {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            print("⏳ Waiting for timeout (6 seconds)...")
            
            # Don't send anything - should timeout
            try:
                response = await websocket.recv()
                print(f"📥 Unexpected response: {response}")
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"✅ Connection closed due to timeout: {e.code} - {e.reason}")
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✅ Connection closed as expected: {e.code} - {e.reason}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all tests."""
    print("🧪 Testing WebSocket Ingest Handshake Protocol")
    print("=" * 50)
    
    await test_handshake_protocol()
    await test_invalid_handshake()
    await test_handshake_timeout()
    
    print("\n🎉 Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
