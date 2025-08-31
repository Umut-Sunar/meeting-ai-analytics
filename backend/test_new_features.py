#!/usr/bin/env python3
"""
Test script for new features: health endpoint, rate limiting, and structured logging.
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import httpx
import websockets
from app.core.config import get_settings


class NewFeaturesTestSuite:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000"
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result with emoji indicators."""
        status = "✅" if success else "❌"
        self.test_results.append((test_name, success, message))
        print(f"{status} {test_name}: {message}")
        
    async def test_health_endpoint(self):
        """Test the updated /api/v1/health endpoint."""
        print("\n🏥 Testing Health Endpoint")
        print("=" * 40)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/health")
                
                if response.status_code == 200:
                    self.log_test("Health endpoint status", True, "200 OK")
                    
                    data = response.json()
                    
                    # Check required fields
                    required_fields = ["redis", "storage", "version"]
                    for field in required_fields:
                        if field in data:
                            self.log_test(f"Health field '{field}'", True, f"Present: {data[field]}")
                        else:
                            self.log_test(f"Health field '{field}'", False, "Missing")
                    
                    # Check field values
                    redis_status = data.get("redis")
                    if redis_status in ["ok", "down"]:
                        self.log_test("Redis status format", True, f"Valid: {redis_status}")
                    else:
                        self.log_test("Redis status format", False, f"Invalid: {redis_status}")
                    
                    storage_status = data.get("storage")
                    if storage_status in ["ok", "down"]:
                        self.log_test("Storage status format", True, f"Valid: {storage_status}")
                    else:
                        self.log_test("Storage status format", False, f"Invalid: {storage_status}")
                    
                    version = data.get("version")
                    if version:
                        self.log_test("Version field", True, f"Present: {version}")
                    else:
                        self.log_test("Version field", False, "Missing or empty")
                        
                else:
                    self.log_test("Health endpoint status", False, f"Status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("Health endpoint connection", False, f"Error: {e}")
            
    async def test_rate_limiting(self):
        """Test WebSocket connection rate limiting."""
        print("\n🚦 Testing Rate Limiting")
        print("=" * 40)
        
        # Generate a fresh JWT token
        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NzE4OTcyLCJpYXQiOjE3NTY2MzI1NzIsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.PbGbZRGyoKT2R9jToqW8DA9Er8Z3cTSzZ8OFBkjTc3_AF1cgXh7bslOXAsvQCAgYPzU_ic-riIvQj6YGnXagXmFdKxA1yHbJaQiQlQ2uJHSDrFpgRIR3FQIBuKlxFaG9xVnEP_QrriiYY6Btpr3fS47SZvZRJ_wy4Mc1Pb51fg9WM1yUmKlIrqpgP1zLg5g5fF5WEP7NAKwJe3yuc2AVrOIvENVbhQWvCb8zFQLfUwdTSIRfZz6nhronpobMjBT-mjG-wfFZ6lhZVUK7Middv_qXqzDA3I0P99eK-JuDbSZZ-pGkzFTAU-PdCPsATKAYgbOOvrazZ9SMedIoEV-xBQ"
        
        meeting_id = "test-rate-limit"
        source = "mic"
        uri = f"{self.ws_url}/api/v1/ws/ingest/meetings/{meeting_id}?source={source}&token={jwt_token}"
        
        # Test normal connection first
        try:
            async with websockets.connect(uri) as websocket:
                # Send handshake
                handshake = {
                    "type": "handshake",
                    "meeting_id": meeting_id,
                    "device_id": "test-device-001",
                    "source": source,
                    "codec": "pcm",
                    "sample_rate": 16000,
                    "channels": 1,
                    "client": "test-client",
                    "version": "1.0.0"
                }
                
                await websocket.send(json.dumps(handshake))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "handshake-ack" and response_data.get("ok"):
                    self.log_test("Normal connection", True, "Handshake successful")
                else:
                    self.log_test("Normal connection", False, f"Unexpected response: {response_data}")
                    
        except Exception as e:
            self.log_test("Normal connection", False, f"Error: {e}")
        
        # Test rate limiting by making multiple rapid connections
        print("Testing rate limiting with rapid connections...")
        
        rate_limit_triggered = False
        successful_connections = 0
        
        for i in range(7):  # Try 7 connections (should trigger rate limit after 5)
            try:
                async with websockets.connect(uri) as websocket:
                    successful_connections += 1
                    print(f"  Connection {i+1}: Success")
                    await asyncio.sleep(0.1)  # Small delay
                    
            except websockets.exceptions.ConnectionClosedError as e:
                if e.code == 1013:  # Rate limit code
                    rate_limit_triggered = True
                    print(f"  Connection {i+1}: Rate limited (code 1013)")
                    break
                else:
                    print(f"  Connection {i+1}: Failed with code {e.code}")
            except Exception as e:
                print(f"  Connection {i+1}: Error - {e}")
        
        if rate_limit_triggered:
            self.log_test("Rate limiting", True, f"Triggered after {successful_connections} connections")
        else:
            self.log_test("Rate limiting", False, f"Not triggered after {successful_connections} connections")
            
    async def test_structured_logging(self):
        """Test structured logging by making a connection and checking logs."""
        print("\n📝 Testing Structured Logging")
        print("=" * 40)
        
        # This test is more observational - we'll make a connection and 
        # check that it doesn't crash (actual log inspection would require log capture)
        
        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NzE4OTcyLCJpYXQiOjE3NTY2MzI1NzIsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.PbGbZRGyoKT2R9jToqW8DA9Er8Z3cTSzZ8OFBkjTc3_AF1cgXh7bslOXAsvQCAgYPzU_ic-riIvQj6YGnXagXmFdKxA1yHbJaQiQlQ2uJHSDrFpgRIR3FQIBuKlxFaG9xVnEP_QrriiYY6Btpr3fS47SZvZRJ_wy4Mc1Pb51fg9WM1yUmKlIrqpgP1zLg5g5fF5WEP7NAKwJe3yuc2AVrOIvENVbhQWvCb8zFQLfUwdTSIRfZz6nhronpobMjBT-mjG-wfFZ6lhZVUK7Middv_qXqzDA3I0P99eK-JuDbSZZ-pGkzFTAU-PdCPsATKAYgbOOvrazZ9SMedIoEV-xBQ"
        
        meeting_id = "test-structured-logging"
        source = "sys"
        uri = f"{self.ws_url}/api/v1/ws/ingest/meetings/{meeting_id}?source={source}&token={jwt_token}"
        
        try:
            print("Making connection to test structured logging...")
            async with websockets.connect(uri) as websocket:
                # Send handshake
                handshake = {
                    "type": "handshake",
                    "meeting_id": meeting_id,
                    "device_id": "test-device-structured",
                    "source": source,
                    "codec": "pcm",
                    "sample_rate": 16000,
                    "channels": 1,
                    "client": "test-client",
                    "version": "1.0.0"
                }
                
                await websocket.send(json.dumps(handshake))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "handshake-ack":
                    self.log_test("Structured logging connection", True, "Connection established with structured logging")
                    
                    # Send some test PCM data
                    test_pcm = b'\x00' * 1024  # 1KB of silence
                    await websocket.send(test_pcm)
                    
                    # Wait a bit for processing
                    await asyncio.sleep(1)
                    
                    self.log_test("Structured logging PCM", True, "PCM data sent successfully")
                else:
                    self.log_test("Structured logging connection", False, f"Handshake failed: {response_data}")
                    
        except Exception as e:
            self.log_test("Structured logging connection", False, f"Error: {e}")
            
    async def test_websocket_endpoints(self):
        """Test that all WebSocket endpoints are accessible."""
        print("\n🔌 Testing WebSocket Endpoints")
        print("=" * 40)
        
        # Test endpoints exist (basic connectivity)
        endpoints = [
            "/api/v1/ws/ingest/meetings/test?source=mic",
            "/api/v1/ws/meetings/test",
            "/transcript/test"
        ]
        
        for endpoint in endpoints:
            try:
                # Just test that the endpoint exists and accepts connections
                # (without proper auth, they should close with auth error)
                uri = f"{self.ws_url}{endpoint}"
                async with websockets.connect(uri) as websocket:
                    # This should fail with auth error, which means endpoint exists
                    pass
            except websockets.exceptions.ConnectionClosedError as e:
                if e.code in [1008, 1002]:  # Auth error or protocol error
                    self.log_test(f"Endpoint {endpoint}", True, "Endpoint accessible (auth required)")
                else:
                    self.log_test(f"Endpoint {endpoint}", False, f"Unexpected close code: {e.code}")
            except Exception as e:
                self.log_test(f"Endpoint {endpoint}", False, f"Error: {e}")
                
    async def run_all_tests(self):
        """Run all tests."""
        print("🧪 New Features Test Suite")
        print("=" * 50)
        print("Testing: Health endpoint, Rate limiting, Structured logging")
        print()
        
        # Run test suites
        await self.test_health_endpoint()
        await self.test_websocket_endpoints()
        await self.test_structured_logging()
        await self.test_rate_limiting()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if message and not success:
                print(f"     └─ {message}")
                
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! New features are working correctly.")
            return True
        else:
            print("💥 Some tests failed. Check the output above for details.")
            return False


async def main():
    """Main test runner."""
    print("🚀 Starting backend server test...")
    print("Make sure the backend is running on http://localhost:8000")
    print()
    
    # Wait a moment for user to confirm
    await asyncio.sleep(2)
    
    tester = NewFeaturesTestSuite()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
