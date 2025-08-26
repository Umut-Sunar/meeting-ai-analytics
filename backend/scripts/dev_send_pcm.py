#!/usr/bin/env python3
"""
Development script to send PCM audio data to ingest WebSocket.
"""

import asyncio
import json
import sys
import wave
import argparse
from typing import Optional, BinaryIO
from datetime import datetime

import websockets

from app.core.security import create_dev_jwt_token


async def send_audio_to_ingest(
    meeting_id: str,
    wav_file_path: str,
    jwt_token: str,
    source: str = "mic",
    ws_url: str = "ws://localhost:8000/api/v1",
    chunk_size: int = 4096
) -> None:
    """
    Send WAV file to ingest WebSocket as PCM data.
    
    Args:
        meeting_id: Meeting ID
        wav_file_path: Path to WAV file (16-bit, mono, 48kHz preferred)
        jwt_token: JWT authentication token
        source: Audio source ("mic" or "system")
        ws_url: WebSocket server URL
        chunk_size: Audio chunk size in bytes
    """
    uri = f"{ws_url}/ws/ingest/meetings/{meeting_id}?token={jwt_token}"
    
    print(f"🔗 Connecting to: {uri}")
    print(f"📅 Meeting ID: {meeting_id}")
    print(f"🎵 WAV file: {wav_file_path}")
    print(f"🎤 Source: {source}")
    print(f"🕐 Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    # Read WAV file info
    try:
        with wave.open(wav_file_path, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
            duration = frame_count / sample_rate
            
            print(f"📊 WAV Info:")
            print(f"    Sample rate: {sample_rate} Hz")
            print(f"    Channels: {channels}")
            print(f"    Sample width: {sample_width} bytes")
            print(f"    Duration: {duration:.2f} seconds")
            print(f"    Frame count: {frame_count}")
            print()
            
            if sample_width != 2:
                print("⚠️  Warning: Expected 16-bit audio (sample_width=2)")
            if channels != 1:
                print("⚠️  Warning: Expected mono audio (channels=1)")
            if sample_rate != 48000:
                print(f"⚠️  Warning: Expected 48kHz audio, got {sample_rate}Hz")
            
    except Exception as e:
        print(f"❌ Error reading WAV file: {e}")
        return
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to ingest WebSocket")
            
            # Send handshake message
            handshake = {
                "type": "handshake",
                "source": source,
                "sample_rate": sample_rate,
                "channels": channels,
                "language": "tr",
                "ai_mode": "standard",
                "device_id": "dev-script-001"
            }
            
            print(f"🤝 Sending handshake: {json.dumps(handshake, indent=2)}")
            await websocket.send(json.dumps(handshake))
            
            # Wait for confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📥 Handshake response: {response_data.get('status', 'unknown')}")
            
            if response_data.get('status') != 'ready':
                print(f"❌ Handshake failed: {response_data}")
                return
            
            print("🎵 Starting audio transmission...")
            
            # Send audio data in chunks
            with wave.open(wav_file_path, 'rb') as wav_file:
                bytes_sent = 0
                chunks_sent = 0
                
                while True:
                    # Read chunk
                    audio_chunk = wav_file.readframes(chunk_size // (sample_width * channels))
                    if not audio_chunk:
                        break
                    
                    # Send binary data
                    await websocket.send(audio_chunk)
                    
                    bytes_sent += len(audio_chunk)
                    chunks_sent += 1
                    
                    # Progress update
                    if chunks_sent % 10 == 0:
                        progress = (bytes_sent / (frame_count * sample_width * channels)) * 100
                        print(f"📤 Sent {chunks_sent} chunks, {bytes_sent} bytes ({progress:.1f}%)")
                    
                    # Small delay to simulate real-time
                    await asyncio.sleep(0.01)
                
                print(f"✅ Audio transmission complete: {chunks_sent} chunks, {bytes_sent} bytes")
            
            # Send finalize message
            finalize_msg = {"type": "finalize"}
            print(f"🏁 Sending finalize: {json.dumps(finalize_msg)}")
            await websocket.send(json.dumps(finalize_msg))
            
            # Wait for final responses
            print("⏳ Waiting for final responses...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    message_type = response_data.get('type', 'unknown')
                    
                    if message_type == 'status':
                        status = response_data.get('status', '')
                        message = response_data.get('message', '')
                        print(f"📊 Status: {status} - {message}")
                        
                        if status == 'finalized':
                            break
                    else:
                        print(f"📥 Response: {message_type}")
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for responses")
            
            print("🎉 Ingest session completed successfully!")
            
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


def create_test_wav_file(file_path: str, duration: float = 5.0) -> None:
    """Create a test WAV file with sine wave."""
    import math
    import struct
    
    sample_rate = 48000
    frequency = 440  # A4 note
    amplitude = 0.3
    
    print(f"🎵 Creating test WAV file: {file_path}")
    print(f"    Duration: {duration}s, Frequency: {frequency}Hz")
    
    with wave.open(file_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(int(sample_rate * duration)):
            # Generate sine wave
            t = i / sample_rate
            sample = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            
            # Add some variation to make it more interesting
            if i % (sample_rate // 2) == 0:
                frequency += 50  # Change frequency every 0.5 seconds
            
            # Pack as 16-bit signed integer
            wav_file.writeframes(struct.pack('<h', sample))
    
    print(f"✅ Test WAV file created: {file_path}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Send PCM audio to ingest WebSocket")
    parser.add_argument("--meeting", required=True, help="Meeting ID")
    parser.add_argument("--wav", help="WAV file path (or create test file)")
    parser.add_argument("--jwt", help="JWT token (or auto-generate)")
    parser.add_argument("--source", default="mic", choices=["mic", "system"], help="Audio source")
    parser.add_argument("--url", default="ws://localhost:8000/api/v1", help="WebSocket URL")
    parser.add_argument("--user-id", default="test-user", help="User ID for test token")
    parser.add_argument("--tenant-id", default="test-tenant", help="Tenant ID for test token")
    parser.add_argument("--chunk-size", type=int, default=4096, help="Audio chunk size")
    parser.add_argument("--create-test-wav", action="store_true", help="Create test WAV file")
    parser.add_argument("--test-duration", type=float, default=5.0, help="Test WAV duration")
    
    args = parser.parse_args()
    
    # Handle WAV file
    wav_file = args.wav
    if args.create_test_wav or not wav_file:
        wav_file = "test_audio.wav"
        create_test_wav_file(wav_file, args.test_duration)
    
    if not wav_file:
        print("❌ WAV file required. Use --wav or --create-test-wav")
        return
    
    # Get or create JWT token
    jwt_token = args.jwt
    if not jwt_token:
        print("🔑 Generating test JWT token...")
        jwt_token = create_test_token(args.user_id, args.tenant_id)
        print(f"    Token: {jwt_token[:50]}...")
    
    # Start ingest
    await send_audio_to_ingest(
        args.meeting, wav_file, jwt_token, args.source, 
        args.url, args.chunk_size
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
