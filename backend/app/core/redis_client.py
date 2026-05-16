"""
Redis Client - Async connection management
"""
import logging
from typing import Any, Optional
import json

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Fallback in-memory cache when Redis is unavailable."""
    
    def __init__(self):
        self._store: dict = {}
        self._ttl: dict = {}
        import time
        self._time = time
    
    async def get(self, key: str) -> Optional[str]:
        if key in self._ttl:
            if self._time.time() > self._ttl[key]:
                del self._store[key]
                del self._ttl[key]
                return None
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: int = None) -> bool:
        import time
        self._store[key] = value
        if ex:
            self._ttl[key] = time.time() + ex
        return True
    
    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            if key in self._ttl:
                del self._ttl[key]
            return 1
        return 0
    
    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val
    
    async def expire(self, key: str, seconds: int) -> bool:
        import time
        self._ttl[key] = time.time() + seconds
        return True
    
    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0
    
    async def lpush(self, key: str, *values) -> int:
        if key not in self._store:
            self._store[key] = []
        for v in values:
            self._store[key].insert(0, v)
        return len(self._store[key])
    
    async def lrange(self, key: str, start: int, end: int):
        lst = self._store.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        if key in self._store:
            self._store[key] = self._store[key][start:end + 1]
        return True
    
    async def ping(self) -> bool:
        return True
    
    async def keys(self, pattern: str = "*"):
        return list(self._store.keys())
    
    async def hset(self, key: str, field: str, value: str) -> int:
        if key not in self._store:
            self._store[key] = {}
        self._store[key][field] = value
        return 1
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        return self._store.get(key, {}).get(field)
    
    async def hgetall(self, key: str) -> dict:
        return self._store.get(key, {})
    
    async def publish(self, channel: str, message: str) -> int:
        return 0  # No-op for in-memory


class RedisClient:
    """Redis client with fallback to in-memory cache."""
    
    def __init__(self):
        self._client = None
        self._fallback = InMemoryCache()
        self._using_redis = False
    
    async def initialize(self):
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed, using in-memory fallback")
            return
        
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._client.ping()
            self._using_redis = True
            logger.info(f"✅ Connected to Redis: {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Using in-memory cache.")
            self._client = None
    
    @property
    def client(self):
        """Get active client (Redis or fallback)."""
        return self._client if self._using_redis else self._fallback
    
    async def ping(self) -> bool:
        """Check if cache is available."""
        try:
            await self.client.ping()
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._client and self._using_redis:
            await self._client.close()
    
    # Convenience methods
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)
    
    async def set(self, key: str, value: Any, ex: int = None) -> bool:
        if not isinstance(value, str):
            value = json.dumps(value)
        return await self.client.set(key, value, ex=ex)
    
    async def get_json(self, key: str) -> Optional[Any]:
        val = await self.get(key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return None
    
    async def delete(self, key: str) -> int:
        return await self.client.delete(key)
    
    async def incr(self, key: str) -> int:
        return await self.client.incr(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        return await self.client.expire(key, seconds)
    
    async def exists(self, key: str) -> bool:
        result = await self.client.exists(key)
        return bool(result)
    
    async def lpush(self, key: str, *values) -> int:
        str_values = [json.dumps(v) if not isinstance(v, str) else v for v in values]
        return await self.client.lpush(key, *str_values)
    
    async def lrange(self, key: str, start: int, end: int):
        return await self.client.lrange(key, start, end)
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        return await self.client.ltrim(key, start, end)
    
    async def publish(self, channel: str, message: Any) -> int:
        if not isinstance(message, str):
            message = json.dumps(message)
        return await self.client.publish(channel, message)
    
    @property
    def is_redis(self) -> bool:
        return self._using_redis


# Singleton
redis_client = RedisClient()
