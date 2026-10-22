from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from redis.asyncio import Redis

from zooffer.config import settings
from zooffer.core.errors import RateLimitedError


class RateLimiter:
    """Fixed-window limiter backed by Redis, with an in-process fallback for dev/tests.

    The in-process fallback is correct for a single process only; production uses Redis.
    """

    def __init__(self, redis_url: str | None = None, *, use_memory: bool = False) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._use_memory = use_memory
        self._redis: Redis | None = None
        self._local: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> tuple[int, int]:
        """Record a hit. Returns (remaining, retry_after_seconds). Raises RateLimitedError."""
        if limit <= 0:
            raise RateLimitedError("Слишком много запросов. Попробуйте позже.", window_seconds)
        if self._use_memory:
            return await self._hit_memory(key, limit, window_seconds)
        try:
            client = await self._client()
            bucket = f"rl:{key}"
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(bucket)
                pipe.ttl(bucket)
                count, ttl = await pipe.execute()
            if int(ttl) < 0:
                await client.expire(bucket, window_seconds)
                ttl = window_seconds
            if int(count) > limit:
                raise RateLimitedError(
                    "Слишком много запросов. Попробуйте позже.", max(int(ttl), 1)
                )
            return max(limit - int(count), 0), max(int(ttl), 1)
        except RateLimitedError:
            raise
        except Exception:
            # Redis outage must not take the whole API down for non-auth actions, but it is
            # logged by the caller. Fall back to the local window.
            return await self._hit_memory(key, limit, window_seconds)

    async def _hit_memory(self, key: str, limit: int, window_seconds: int) -> tuple[int, int]:
        now = time.monotonic()
        async with self._lock:
            bucket = self._local[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(int(bucket[0] + window_seconds - now), 1)
                raise RateLimitedError("Слишком много запросов. Попробуйте позже.", retry_after)
            bucket.append(now)
            remaining = limit - len(bucket)
            retry_after = window_seconds
        return remaining, retry_after

    async def reset(self, key: str) -> None:
        self._local.pop(key, None)
        if self._use_memory or self._redis is None:
            return
        try:
            await self._redis.delete(f"rl:{key}")
        except Exception:
            return

    def clear_local(self) -> None:
        """Test helper: drop all in-process windows."""
        self._local.clear()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


limiter = RateLimiter(use_memory=settings.environment in {"dev", "test"})
