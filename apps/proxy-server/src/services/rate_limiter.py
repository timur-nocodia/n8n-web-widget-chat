import asyncio
import time
from typing import Optional, Dict, Any
import redis.asyncio as redis
from core.config import settings
from core.exceptions import RateLimitExceededError


class RateLimiter:
    def __init__(self):
        self.redis_client = None
        self._connection_pool = None

    async def _get_redis(self):
        if not self.redis_client:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.redis_client = redis.Redis(connection_pool=self._connection_pool)
        return self.redis_client

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        identifier: str = "request"
    ) -> Dict[str, Any]:
        """
        Check rate limit using sliding window algorithm
        Returns: {
            "allowed": bool,
            "count": int,
            "reset_time": int,
            "retry_after": int
        }
        """
        redis_client = await self._get_redis()
        
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {f"{current_time}:{identifier}": current_time})
        
        # Set expiration
        pipe.expire(key, window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1] + 1  # +1 for the request we just added
        
        reset_time = current_time + window_seconds
        retry_after = 0
        
        if current_count > limit:
            # Remove the request we just added since it's over limit
            await redis_client.zrem(key, f"{current_time}:{identifier}")
            
            # Calculate retry after time
            oldest_requests = await redis_client.zrange(
                key, 0, 0, withscores=True
            )
            if oldest_requests:
                oldest_time = int(oldest_requests[0][1])
                retry_after = max(0, oldest_time + window_seconds - current_time)
            
            return {
                "allowed": False,
                "count": current_count - 1,
                "limit": limit,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "window_seconds": window_seconds
            }
        
        return {
            "allowed": True,
            "count": current_count,
            "limit": limit,
            "reset_time": reset_time,
            "retry_after": 0,
            "window_seconds": window_seconds
        }

    async def check_ip_rate_limit(self, ip_address: str) -> Dict[str, Any]:
        """Check rate limit for IP address"""
        # Per-minute limit
        minute_result = await self.check_rate_limit(
            f"rate_limit:ip:{ip_address}:minute",
            settings.rate_limit_per_minute,
            60,
            f"ip_{ip_address}"
        )
        
        if not minute_result["allowed"]:
            return minute_result
        
        # Per-hour limit
        hour_result = await self.check_rate_limit(
            f"rate_limit:ip:{ip_address}:hour",
            settings.rate_limit_per_hour,
            3600,
            f"ip_{ip_address}"
        )
        
        return hour_result

    async def check_session_rate_limit(
        self, 
        session_id: str,
        limit_per_minute: int = 30
    ) -> Dict[str, Any]:
        """Check rate limit for session"""
        return await self.check_rate_limit(
            f"rate_limit:session:{session_id}:minute",
            limit_per_minute,
            60,
            f"session_{session_id}"
        )

    async def check_domain_rate_limit(
        self, 
        domain: str,
        limit_per_minute: int = 1000
    ) -> Dict[str, Any]:
        """Check rate limit for domain"""
        return await self.check_rate_limit(
            f"rate_limit:domain:{domain}:minute",
            limit_per_minute,
            60,
            f"domain_{domain}"
        )

    async def increment_counter(self, key: str, ttl: int = 3600) -> int:
        """Simple counter with expiration"""
        redis_client = await self._get_redis()
        
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        
        results = await pipe.execute()
        return results[0]

    async def is_blocked(self, key: str) -> bool:
        """Check if a key is blocked"""
        redis_client = await self._get_redis()
        blocked_until = await redis_client.get(f"blocked:{key}")
        
        if blocked_until:
            if int(blocked_until) > time.time():
                return True
            else:
                # Block has expired, remove it
                await redis_client.delete(f"blocked:{key}")
        
        return False

    async def block_key(self, key: str, duration_seconds: int):
        """Block a key for specified duration"""
        redis_client = await self._get_redis()
        block_until = int(time.time()) + duration_seconds
        
        await redis_client.setex(
            f"blocked:{key}",
            duration_seconds,
            block_until
        )

    async def get_rate_limit_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get current rate limit info for debugging"""
        redis_client = await self._get_redis()
        
        current_time = int(time.time())
        count = await redis_client.zcard(key)
        ttl = await redis_client.ttl(key)
        
        if ttl == -1:  # Key exists but no expiration
            ttl = 0
        elif ttl == -2:  # Key doesn't exist
            return None
        
        return {
            "key": key,
            "count": count,
            "ttl": ttl,
            "current_time": current_time
        }


# Global rate limiter instance
rate_limiter = RateLimiter()