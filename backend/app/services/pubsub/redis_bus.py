import asyncio
import json
import logging
import contextlib
from typing import Any, Dict, Optional, Callable, Awaitable
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
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
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
            raise RuntimeError("Redis not connected")
            
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
            raise RuntimeError("Redis not connected")
            
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
            raise RuntimeError("Redis not connected")
            
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