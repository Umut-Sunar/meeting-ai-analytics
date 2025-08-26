#!/usr/bin/env python3
"""
Development script to test WebSocket subscription to meeting transcripts.
"""

import asyncio
import json
import sys
from typing import Optional

import websockets
import argparse
from datetime import datetime

from app.core.security import create_dev_jwt_token


async def subscribe_to_meeting(
    meeting_id: str,
    jwt_token: str,
    ws_url: str = "ws://localhost:8000/api/v1"
) -> None:
    """
    Subscribe to meeting transcripts via WebSocket.
    
    Args:
        meeting_id: Meeting ID to subscribe to
        jwt_token: JWT authentication token
        ws_url: WebSocket server URL
    """
    uri = f"{ws_url}/ws/meetings/{meeting_id}?token={jwt_token}"
    
    print(f"🔗 Connecting to: {uri}")
    print(f"📅 Meeting ID: {meeting_id}")
    print(f"🕐 Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    timestamp = data.get("ts", "")
                    
                    if message_type == "transcript.partial":
                        print(f"🟡 PARTIAL [{data.get('segment_no', 0)}]: {data.get('text', '')}")
                        
                    elif message_type == "transcript.final":
                        confidence = data.get('confidence', 0.0)
                        speaker = data.get('speaker', 'Unknown')
                        duration = data.get('end_ms', 0) - data.get('start_ms', 0)
                        
                        print(f"🟢 FINAL   [{data.get('segment_no', 0)}]: {data.get('text', '')}")
                        print(f"    └─ Speaker: {speaker}, Confidence: {confidence:.2f}, Duration: {duration}ms")
                        
                    elif message_type == "status":
                        status = data.get('status', '')
                        message_text = data.get('message', '')
                        print(f"📊 STATUS: {status} - {message_text}")
                        
                    elif message_type == "error":
                        error_code = data.get('error_code', '')
                        error_message = data.get('error_message', '')
                        print(f"❌ ERROR: {error_code} - {error_message}")
                        
                    elif message_type == "ai.tip":
                        tip_type = data.get('tip_type', '')
                        content = data.get('content', '')
                        print(f"💡 AI TIP ({tip_type}): {content}")
                        
                    else:
                        print(f"❓ UNKNOWN MESSAGE: {message_type}")
                        
                    # Show timestamp
                    if timestamp:
                        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        print(f"    └─ Time: {ts.strftime('%H:%M:%S.%f')[:-3]}")
                    
                    print()
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON: {e}")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    
    except websockets.exceptions.ConnectionClosed:
        print("📤 Connection closed")
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Connection error: {e}")


def create_test_token(user_id: str = "test-user", tenant_id: str = "test-tenant") -> str:
    """Create a test JWT token."""
    return create_dev_jwt_token(
        user_id=user_id,
        tenant_id=tenant_id,
        email="test@example.com",
        role="user"
    )


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Subscribe to meeting transcripts via WebSocket")
    parser.add_argument("--meeting", required=True, help="Meeting ID")
    parser.add_argument("--jwt", help="JWT token (or auto-generate)")
    parser.add_argument("--url", default="ws://localhost:8000/api/v1", help="WebSocket URL")
    parser.add_argument("--user-id", default="test-user", help="User ID for test token")
    parser.add_argument("--tenant-id", default="test-tenant", help="Tenant ID for test token")
    
    args = parser.parse_args()
    
    # Get or create JWT token
    jwt_token = args.jwt
    if not jwt_token:
        print("🔑 Generating test JWT token...")
        jwt_token = create_test_token(args.user_id, args.tenant_id)
        print(f"    Token: {jwt_token[:50]}...")
    
    # Start subscription
    await subscribe_to_meeting(args.meeting, jwt_token, args.url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
