import asyncio
import json
import logging
import contextlib
from typing import Any, Dict, Optional, Callable, Awaitable
from urllib.parse import urlparse, urlunparse
from redis import asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisBus:
    """Redis pub/sub wrapper for real-time messaging."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribers: Dict[str, Callable[[str, Dict[str, Any]], Awaitable[None]]] = {}
        self._listen_task: Optional[asyncio.Task] = None
        
    def _build_redis_url(self) -> tuple[str, str]:
        """Build Redis URL with password and return (url, masked_url) for logging."""
        redis_url = settings.REDIS_URL
        
        # Parse URL to check for existing password
        parsed = urlparse(redis_url)
        
        # If REDIS_PASSWORD is set but URL has no password, add it
        if settings.REDIS_PASSWORD and not parsed.password:
            # Reconstruct URL with password
            netloc = f":{settings.REDIS_PASSWORD}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            
            redis_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        
        # Create masked URL for logging
        if parsed.password or settings.REDIS_PASSWORD:
            masked_netloc = f":***@{parsed.hostname}"
            if parsed.port:
                masked_netloc += f":{parsed.port}"
            
            masked_url = urlunparse((
                parsed.scheme,
                masked_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        else:
            masked_url = redis_url
            
        return redis_url, masked_url

    async def connect(self):
        """Connect to Redis with AUTH support and fail-fast if required."""
        try:
            redis_url, masked_url = self._build_redis_url()
            logger.info(f"Attempting to connect to Redis: {masked_url}")
            
            self.redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,  # 5 second timeout
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection with PING
            await self.redis.ping()
            
            # Get connection info for logging
            info = await self.redis.info()
            redis_version = info.get('redis_version', 'unknown')
            
            # Parse URL for connection details
            parsed = urlparse(settings.REDIS_URL)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 6379
            db = parsed.path.lstrip('/') or '0'
            auth_status = "on" if (parsed.password or settings.REDIS_PASSWORD) else "off"
            
            logger.info(f"✅ Redis connected: host={host}, port={port}, db={db}, auth={auth_status}, version={redis_version}")
            logger.info("📋 Ensure only one Redis runs. If Docker is used, do not start host redis.")
            
        except Exception as e:
            error_msg = f"❌ Failed to connect to Redis: {e}"
            logger.error(error_msg)
            
            # Parse URL for error logging
            parsed = urlparse(settings.REDIS_URL)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 6379
            logger.error(f"Redis connection details: host={host}, port={port}")
            
            if settings.REDIS_REQUIRED:
                logger.error("🚨 REDIS_REQUIRED=true - stopping startup")
                logger.error("💡 Hint: Check if Redis is running and password is correct")
                logger.error("💡 For Docker: export REDIS_PASSWORD=dev_redis_password && docker compose up -d redis")
                raise RuntimeError(f"Redis connection required but failed: {e}")
            else:
                logger.warning("⚠️ Redis not available - transcript streaming will be disabled")
                self.redis = None
            
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
                
        if self.pubsub:
            await self.pubsub.close()
            
        if self.redis:
            await self.redis.aclose()
            
        logger.info("Disconnected from Redis")
        
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to channel."""
        if not self.redis:
            logger.warning(f"Redis not connected - skipping publish to {channel}")
            return
            
        try:
            message_str = json.dumps(message)
            await self.redis.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {message_str[:100]}...")
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise
            
    async def subscribe(self, channel: str, handler: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """Subscribe to channel with handler."""
        if not self.redis:
            logger.warning(f"Redis not connected - skipping subscription to {channel}")
            return
            
        self.subscribers[channel] = handler
        
        if not self.pubsub:
            self.pubsub = self.redis.pubsub()
            
        await self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")
        
        # Start listening if not already started
        if not self._listen_task:
            self._listen_task = asyncio.create_task(self._listen_loop())
            
    async def unsubscribe(self, channel: str):
        """Unsubscribe from channel."""
        if channel in self.subscribers:
            del self.subscribers[channel]
            
        if self.pubsub:
            await self.pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from channel: {channel}")
            
    async def _listen_loop(self):
        """Listen for messages and dispatch to handlers."""
        if not self.pubsub:
            return
            
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    payload = json.loads(message["data"])
                    if handler := self.subscribers.get(channel):
                        try:
                            await handler(channel, payload)
                        except Exception as e:
                            logger.error(f"Error handling message from {channel}: {e}")
                            
        except asyncio.CancelledError:
            logger.info("Redis listen loop cancelled")
        except Exception as e:
            logger.error(f"Error in Redis listen loop: {e}")

    def get_meeting_transcript_topic(self, meeting_id: str) -> str:
        """Get transcript topic for a meeting."""
        return f"meeting:{meeting_id}:transcript"
        
    def get_meeting_status_topic(self, meeting_id: str) -> str:
        """Get status topic for a meeting."""
        return f"meeting:{meeting_id}:status"
        
    async def subscribe_generator(self, channel: str):
        """Subscribe to channel and yield messages as async generator."""
        if not self.redis:
            logger.warning(f"Redis not connected - no messages will be yielded for {channel}")
            return  # Empty generator
            
        pubsub = self.redis.pubsub()
        try:
            await pubsub.subscribe(channel)
            logger.info(f"Generator subscribed to channel: {channel}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
                    
        except asyncio.CancelledError:
            logger.info(f"Generator subscription to {channel} cancelled")
        except Exception as e:
            logger.error(f"Error in generator subscription to {channel}: {e}")
        finally:
            await pubsub.close()


# Global instance
redis_bus = RedisBus()