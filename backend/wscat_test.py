#!/usr/bin/env python3
"""
Manual WebSocket test similar to wscat
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    # JWT token from our previous test
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NzE2OTEzLCJpYXQiOjE3NTY2MzA1MTMsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.XzmFKr0IRtjryqCGfuAvP33MLZqoYX36rDH-lBw8tVHwu9pyTqlQbsH_5Zdx0vJSBMLUtQpo9dOYsvb4xQIEqPe5EpVBpb5GWyvi3Xfa6G15Pr7MYUx1oTtv53Mj4BTpmOImGcy0qZ81hoXb056MRJZ-e-LoIYssxYxfUE5m59a7ac-RrfuUO-8bgGtSYX_t_uJ0ykqlSC8Jf6tOywGcegjLz_El-7pKjtcsO-GQButj49b2PlRN933FhZAr412adpuCHvCd2xcq9RXze_LAzMrF-0qQ12ykAbGv-9A_0rmTOoyEKI75xENeLJKpHJ9Za6ykXAN_xhlnH31S6uRLew"
    
    uri = f"ws://127.0.0.1:8000/api/v1/ws/ingest/meetings/test?source=mic&token={jwt_token}"
    
    print("🔌 Connecting to WebSocket...")
    print(f"URI: {uri}")
    print("=" * 80)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Send handshake message
            handshake_msg = {
                "type": "handshake",
                "meeting_id": "test",
                "device_id": "cli-mic",
                "source": "mic",
                "codec": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1,
                "client": "cli",
                "version": "dev"
            }
            
            print(f"📤 Sending handshake:")
            print(f"   {json.dumps(handshake_msg, indent=2)}")
            
            await websocket.send(json.dumps(handshake_msg))
            
            # Wait for response
            print("⏳ Waiting for handshake response...")
            response = await websocket.recv()
            
            print(f"📥 Received response:")
            try:
                response_json = json.loads(response)
                print(f"   {json.dumps(response_json, indent=2)}")
                
                if response_json.get("type") == "handshake-ack" and response_json.get("ok") is True:
                    print("🎉 SUCCESS: Handshake acknowledged!")
                else:
                    print("❌ UNEXPECTED: Response is not handshake-ack")
                    
            except json.JSONDecodeError:
                print(f"   Raw: {response}")
            
            # Keep connection open for a moment
            print("⏳ Keeping connection open for 2 seconds...")
            await asyncio.sleep(2)
            
            print("👋 Closing connection...")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
