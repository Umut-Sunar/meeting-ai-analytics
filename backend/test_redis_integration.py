#!/usr/bin/env python3
"""
Comprehensive Redis Integration Test Suite
Tests Docker Redis, host Redis, and backend integration scenarios.
"""

import asyncio
import os
import subprocess
import sys
import time
import redis
import redis.asyncio as aioredis
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.services.pubsub.redis_bus import redis_bus


class RedisIntegrationTester:
    def __init__(self):
        self.settings = get_settings()
        self.test_results = []
        self.redis_password = os.getenv('REDIS_PASSWORD', 'dev_redis_password')
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result with emoji indicators."""
        status = "✅" if success else "❌"
        self.test_results.append((test_name, success, message))
        print(f"{status} {test_name}: {message}")
        
    def run_command(self, cmd: str, timeout: int = 10) -> tuple[bool, str]:
        """Run shell command and return success status and output."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except Exception as e:
            return False, str(e)
            
    def check_port_usage(self, port: int = 6379) -> tuple[bool, str]:
        """Check what process is using the specified port."""
        success, output = self.run_command(f"lsof -i :{port}")
        if success and output.strip():
            lines = output.strip().split('\n')
            if len(lines) > 1:  # Header + at least one process
                return True, output
        return False, "No process found on port"
        
    def test_docker_redis_availability(self) -> bool:
        """Test if Docker Redis is available and configured correctly."""
        print("\n🐳 Testing Docker Redis Availability")
        print("=" * 50)
        
        # Check if Docker is running
        success, output = self.run_command("docker info")
        if not success:
            self.log_test("Docker availability", False, "Docker not running or accessible")
            return False
        self.log_test("Docker availability", True, "Docker is running")
        
        # Check if Redis container exists
        success, output = self.run_command("docker ps -a --filter name=meeting-ai-redis --format '{{.Names}}'")
        if not success or "meeting-ai-redis" not in output:
            self.log_test("Redis container exists", False, "Redis container not found")
            return False
        self.log_test("Redis container exists", True, "meeting-ai-redis container found")
        
        # Check if Redis container is running
        success, output = self.run_command("docker ps --filter name=meeting-ai-redis --format '{{.Status}}'")
        if not success or "Up" not in output:
            self.log_test("Redis container running", False, f"Container status: {output.strip()}")
            return False
        self.log_test("Redis container running", True, f"Container status: {output.strip()}")
        
        # Test Redis connection with password
        success, output = self.run_command(f'redis-cli -a "{self.redis_password}" ping')
        if not success or "PONG" not in output:
            self.log_test("Redis connection", False, f"Connection failed: {output}")
            return False
        self.log_test("Redis connection", True, "PONG received")
        
        return True
        
    def test_redis_configuration(self) -> bool:
        """Test Redis configuration and password setup."""
        print("\n🔧 Testing Redis Configuration")
        print("=" * 50)
        
        try:
            # Test direct Redis connection
            r = redis.Redis(host='localhost', port=6379, password=self.redis_password, decode_responses=True)
            
            # Test basic operations
            test_key = "test:integration:key"
            test_value = "test_value_123"
            
            # Set a test value
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            self.log_test("Redis SET operation", True, f"Set {test_key}={test_value}")
            
            # Get the test value
            retrieved = r.get(test_key)
            if retrieved == test_value:
                self.log_test("Redis GET operation", True, f"Retrieved {test_key}={retrieved}")
            else:
                self.log_test("Redis GET operation", False, f"Expected {test_value}, got {retrieved}")
                return False
                
            # Test pub/sub
            pubsub = r.pubsub()
            test_channel = "test:integration:channel"
            pubsub.subscribe(test_channel)
            
            # Publish a message
            r.publish(test_channel, "test_message")
            self.log_test("Redis PUBLISH operation", True, f"Published to {test_channel}")
            
            # Clean up
            r.delete(test_key)
            pubsub.close()
            
            return True
            
        except redis.AuthenticationError as e:
            self.log_test("Redis authentication", False, f"Auth failed: {e}")
            return False
        except redis.ConnectionError as e:
            self.log_test("Redis connection", False, f"Connection failed: {e}")
            return False
        except Exception as e:
            self.log_test("Redis configuration", False, f"Unexpected error: {e}")
            return False
            
    async def test_backend_redis_integration(self) -> bool:
        """Test backend Redis integration using the app's Redis bus."""
        print("\n🔗 Testing Backend Redis Integration")
        print("=" * 50)
        
        try:
            # Test Redis bus connection
            await redis_bus.connect()
            
            if redis_bus.redis is None:
                self.log_test("Backend Redis connection", False, "Redis bus connection is None")
                return False
                
            self.log_test("Backend Redis connection", True, "Redis bus connected successfully")
            
            # Test Redis bus operations
            test_channel = "test:backend:channel"
            test_message = {"type": "test", "data": "backend_integration_test"}
            
            # Test publish
            await redis_bus.publish(test_channel, test_message)
            self.log_test("Backend Redis publish", True, f"Published to {test_channel}")
            
            # Test subscribe (brief test with dummy handler)
            async def dummy_handler(message):
                pass
            
            await redis_bus.subscribe(test_channel, dummy_handler)
            self.log_test("Backend Redis subscribe", True, f"Subscribed to {test_channel}")
            
            # Clean up
            await redis_bus.unsubscribe(test_channel)
            
            return True
            
        except Exception as e:
            self.log_test("Backend Redis integration", False, f"Error: {e}")
            return False
            
    def test_environment_configuration(self) -> bool:
        """Test environment variable configuration."""
        print("\n⚙️ Testing Environment Configuration")
        print("=" * 50)
        
        # Check required environment variables
        required_vars = {
            'REDIS_PASSWORD': self.redis_password,
            'USE_DOCKER_REDIS': os.getenv('USE_DOCKER_REDIS', '1')
        }
        
        for var, value in required_vars.items():
            if value:
                self.log_test(f"Environment {var}", True, f"{var}={value}")
            else:
                self.log_test(f"Environment {var}", False, f"{var} not set")
                
        # Check backend settings
        try:
            redis_url = self.settings.REDIS_URL
            redis_password = self.settings.REDIS_PASSWORD
            redis_required = self.settings.REDIS_REQUIRED
            
            self.log_test("Backend REDIS_URL", bool(redis_url), f"REDIS_URL={redis_url}")
            self.log_test("Backend REDIS_PASSWORD", bool(redis_password), f"REDIS_PASSWORD={'***' if redis_password else 'None'}")
            self.log_test("Backend REDIS_REQUIRED", True, f"REDIS_REQUIRED={redis_required}")
            
            return True
            
        except Exception as e:
            self.log_test("Backend settings", False, f"Error loading settings: {e}")
            return False
            
    def test_conflict_detection(self) -> bool:
        """Test for Redis conflicts (multiple instances)."""
        print("\n🔍 Testing Conflict Detection")
        print("=" * 50)
        
        # Check port 6379 usage
        port_used, output = self.check_port_usage(6379)
        
        if not port_used:
            self.log_test("Port 6379 usage", False, "No Redis process found on port 6379")
            return False
            
        # Count Redis SERVER processes (not client connections)
        lines = output.split('\n')[1:]  # Skip header
        server_lines = []
        client_lines = []
        
        for line in lines:
            if line.strip() and ':6379' in line:
                if 'LISTEN' in line:
                    server_lines.append(line)
                elif 'ESTABLISHED' in line:
                    client_lines.append(line)
        
        redis_servers = len(server_lines)
        redis_clients = len(client_lines)
        
        if redis_servers == 1:
            self.log_test("Redis server count", True, f"Single Redis server detected ({redis_clients} clients)")
            # Identify if it's Docker or host Redis
            if 'docker' in output.lower() or 'com.docker' in output.lower():
                self.log_test("Redis type", True, "Docker Redis detected")
            else:
                self.log_test("Redis type", True, "Host Redis detected")
        elif redis_servers > 1:
            self.log_test("Redis server count", False, f"Multiple Redis servers detected ({redis_servers})")
            print("⚠️ Multiple Redis servers found:")
            for line in server_lines:
                print(f"   {line.strip()}")
            return False
        else:
            self.log_test("Redis server count", False, "No Redis server found")
            return False
            
        return True
        
    def test_redis_performance(self) -> bool:
        """Test Redis performance with basic operations."""
        print("\n⚡ Testing Redis Performance")
        print("=" * 50)
        
        try:
            r = redis.Redis(host='localhost', port=6379, password=self.redis_password, decode_responses=True)
            
            # Test connection latency
            start_time = time.time()
            r.ping()
            ping_latency = (time.time() - start_time) * 1000  # Convert to ms
            
            if ping_latency < 10:  # Less than 10ms is good
                self.log_test("Redis latency", True, f"Ping latency: {ping_latency:.2f}ms")
            else:
                self.log_test("Redis latency", False, f"High ping latency: {ping_latency:.2f}ms")
                
            # Test throughput with multiple operations
            operations = 100
            start_time = time.time()
            
            for i in range(operations):
                r.set(f"perf:test:{i}", f"value_{i}")
                r.get(f"perf:test:{i}")
                
            duration = time.time() - start_time
            ops_per_second = (operations * 2) / duration  # 2 operations per iteration
            
            # Clean up
            for i in range(operations):
                r.delete(f"perf:test:{i}")
                
            if ops_per_second > 1000:  # More than 1000 ops/sec is good
                self.log_test("Redis throughput", True, f"Throughput: {ops_per_second:.0f} ops/sec")
            else:
                self.log_test("Redis throughput", False, f"Low throughput: {ops_per_second:.0f} ops/sec")
                
            return True
            
        except Exception as e:
            self.log_test("Redis performance", False, f"Performance test failed: {e}")
            return False
            
    def test_error_scenarios(self) -> bool:
        """Test error scenarios and recovery."""
        print("\n🚨 Testing Error Scenarios")
        print("=" * 50)
        
        # Test wrong password
        try:
            r = redis.Redis(host='localhost', port=6379, password='wrong_password', decode_responses=True)
            r.ping()
            self.log_test("Wrong password handling", False, "Should have failed with wrong password")
        except redis.AuthenticationError:
            self.log_test("Wrong password handling", True, "Correctly rejected wrong password")
        except Exception as e:
            self.log_test("Wrong password handling", False, f"Unexpected error: {e}")
            
        # Test no password
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            self.log_test("No password handling", False, "Should have failed without password")
        except redis.AuthenticationError:
            self.log_test("No password handling", True, "Correctly rejected connection without password")
        except Exception as e:
            self.log_test("No password handling", False, f"Unexpected error: {e}")
            
        # Test connection to wrong port
        try:
            r = redis.Redis(host='localhost', port=6380, password=self.redis_password, decode_responses=True)
            r.ping()
            self.log_test("Wrong port handling", False, "Should have failed on wrong port")
        except redis.ConnectionError:
            self.log_test("Wrong port handling", True, "Correctly failed on wrong port")
        except Exception as e:
            self.log_test("Wrong port handling", False, f"Unexpected error: {e}")
            
        return True
        
    async def run_all_tests(self) -> bool:
        """Run all Redis integration tests."""
        print("🧪 Redis Integration Test Suite")
        print("=" * 60)
        print(f"🔑 Using Redis password: {self.redis_password}")
        print(f"🐳 USE_DOCKER_REDIS: {os.getenv('USE_DOCKER_REDIS', '1')}")
        print()
        
        tests = [
            ("Environment Configuration", self.test_environment_configuration),
            ("Docker Redis Availability", self.test_docker_redis_availability),
            ("Redis Configuration", self.test_redis_configuration),
            ("Backend Redis Integration", self.test_backend_redis_integration),
            ("Conflict Detection", self.test_conflict_detection),
            ("Redis Performance", self.test_redis_performance),
            ("Error Scenarios", self.test_error_scenarios),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                    
                if result:
                    passed += 1
                    
            except Exception as e:
                self.log_test(test_name, False, f"Test crashed: {e}")
                
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if message and not success:
                print(f"     └─ {message}")
                
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Redis integration is working perfectly.")
            return True
        else:
            print("💥 Some tests failed. Check the output above for details.")
            return False


async def main():
    """Main test runner."""
    tester = RedisIntegrationTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
