"""
BlockScope Rate Limiting Middleware.

Implements sliding window rate limiting backed by Redis, with automatic
in-memory fallback when Redis is unreachable.

Architecture:
    - Primary: Redis sorted-set based sliding window (accurate, distributed)
    - Fallback: Simple in-memory counter (per-IP, per-minute only)
    - Auto-recovery: Switches back to Redis once connectivity is restored
"""

import collections
import logging
import time
import threading
from typing import Callable, Optional

import redis.asyncio as aioredis
from app.core.config import settings
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("blockscope.ratelimit")

# ==================== Redis Connection (Legacy Compat) ====================


class RateLimitRedis:
    """
    Redis connection manager for rate limiting.

    .. deprecated::
        Use ``app.core.redis.redis_manager`` instead.  This class is
        retained for backward compatibility and now delegates to the
        centralised ``RedisManager``.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self):
        """Establish Redis connection via the centralised RedisManager."""
        try:
            from app.core.redis import redis_manager

            if not redis_manager.is_available:
                await redis_manager.connect(
                    url=settings.redis_url_str,
                    password=settings.REDIS_PASSWORD,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                )
        except Exception as exc:
            logger.warning("RateLimitRedis.connect() failed: %s", exc)

    async def disconnect(self):
        """Disconnect via the centralised RedisManager."""
        try:
            from app.core.redis import redis_manager
            await redis_manager.disconnect()
        except Exception:
            pass

    @property
    def redis(self) -> aioredis.Redis:
        """Get Redis client from the centralised manager."""
        from app.core.redis import redis_manager
        return redis_manager.redis


rate_limit_redis = RateLimitRedis()


# ==================== In-Memory Fallback ====================


class _InMemoryRateLimiter:
    """
    Simple in-memory rate limiter used when Redis is unavailable.

    Uses a sliding window counter per identifier (IP/API key).
    Only tracks per-minute limits to keep memory bounded.

    Note: ``is_rate_limited()`` is synchronous and acquires a
    ``threading.Lock``.  This is safe in async context because
    the critical section is sub-microsecond (dict lookups + deque
    operations), so event-loop blocking is negligible.
    """

    # Hard cap on tracked identifiers to prevent memory exhaustion
    # under DDoS with many unique IPs.
    MAX_IDENTIFIERS: int = 10_000

    def __init__(self) -> None:
        self._windows: dict[str, collections.deque] = {}
        self._lock = threading.Lock()
        # Clean up stale entries every 500 calls
        self._cleanup_counter = 0

    def is_rate_limited(self, identifier: str, per_minute: int) -> tuple[bool, dict]:
        """
        Check if the identifier has exceeded per-minute limit.

        Returns:
            (is_limited, info_dict)
        """
        now = time.time()
        cutoff = now - 60.0

        with self._lock:
            # Periodic cleanup of stale identifiers
            self._cleanup_counter += 1
            if self._cleanup_counter >= 500:
                self._cleanup(cutoff)
                self._cleanup_counter = 0

            if identifier not in self._windows:
                # Enforce hard cap to prevent memory exhaustion
                if len(self._windows) >= self.MAX_IDENTIFIERS:
                    self._evict_oldest()
                self._windows[identifier] = collections.deque()

            window = self._windows[identifier]

            # Remove expired entries
            while window and window[0] < cutoff:
                window.popleft()

            count = len(window)

            if count >= per_minute:
                retry_after = int(window[0] + 60 - now) if window else 1
                return True, {
                    "limited": True,
                    "retry_after": max(1, retry_after),
                    "limit": per_minute,
                    "remaining": 0,
                    "reset": int(now + 60),
                    "window": "minute",
                }

            # Record this request
            window.append(now)

            return False, {
                "limited": False,
                "retry_after": 0,
                "limit": per_minute,
                "remaining": max(0, per_minute - count - 1),
                "reset": int(now + 60),
                "window": "minute",
            }

    def _cleanup(self, cutoff: float) -> None:
        """Remove identifiers with no recent requests."""
        stale = [
            k for k, v in self._windows.items()
            if not v or v[-1] < cutoff
        ]
        for k in stale:
            del self._windows[k]

    def _evict_oldest(self) -> None:
        """Evict the identifier with the oldest last-seen timestamp."""
        if not self._windows:
            return
        oldest_key = min(
            self._windows,
            key=lambda k: self._windows[k][-1] if self._windows[k] else 0.0,
        )
        del self._windows[oldest_key]


_fallback_limiter = _InMemoryRateLimiter()


# ==================== Rate Limiting Logic ====================


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Implements token bucket algorithm with Redis sorted sets.
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None, prefix: str = "ratelimit"):
        self._redis = redis_client
        self.prefix = prefix

    def _get_redis(self) -> Optional[aioredis.Redis]:
        """
        Get Redis client, returning None if unavailable.

        This enables graceful degradation to the in-memory fallback.
        """
        if self._redis:
            return self._redis
        try:
            from app.core.redis import redis_manager

            if redis_manager.is_available:
                return redis_manager.redis
        except Exception:
            pass
        return None

    @property
    def redis(self) -> aioredis.Redis:
        """Get Redis client (raises if unavailable)."""
        r = self._get_redis()
        if r is None:
            raise RuntimeError("Redis not available for rate limiting")
        return r

    def _get_key(self, identifier: str, window: str) -> str:
        """
        Generate Redis key for rate limit.

        Args:
            identifier: Unique identifier (IP, API key, user ID)
            window: Time window (minute, hour, day)

        Returns:
            str: Redis key
        """
        return f"{self.prefix}:{identifier}:{window}"

    async def is_rate_limited(
        self, identifier: str, limits: dict, burst_allowance: int = 0
    ) -> tuple[bool, dict]:
        """
        Check if request should be rate limited.

        Falls back to in-memory limiting when Redis is unreachable.

        Args:
            identifier: Unique identifier
            limits: Rate limits dict {per_minute, per_hour, per_day}
            burst_allowance: Allow burst requests beyond limit

        Returns:
            tuple: (is_limited, limit_info)
        """
        redis_client = self._get_redis()

        # ── Fallback: in-memory rate limiting ──
        if redis_client is None:
            per_min = limits.get("per_minute", 60)
            return _fallback_limiter.is_rate_limited(identifier, per_min)

        # ── Primary: Redis-based sliding window ──
        current_time = time.time()

        # Check each window
        windows = {
            "minute": (60, limits.get("per_minute", 0)),
            "hour": (3600, limits.get("per_hour", 0)),
            "day": (86400, limits.get("per_day", 0)),
        }

        limit_info = {
            "limited": False,
            "retry_after": 0,
            "limit": 0,
            "remaining": 0,
            "reset": 0,
            "window": "",
        }

        try:
            for window_name, (window_seconds, limit) in windows.items():
                if limit == 0:  # Skip if limit not set
                    continue

                key = self._get_key(identifier, window_name)

                # Remove old requests outside window
                cutoff_time = current_time - window_seconds
                await redis_client.zremrangebyscore(key, "-inf", cutoff_time)

                # Count requests in current window
                count = await redis_client.zcard(key)

                # Check if limit exceeded (with burst allowance)
                effective_limit = limit + burst_allowance

                if count >= effective_limit:
                    # Rate limited!
                    oldest = await redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        oldest_time = oldest[0][1]
                        retry_after = int(oldest_time + window_seconds - current_time)

                        limit_info.update(
                            {
                                "limited": True,
                                "retry_after": max(1, retry_after),
                                "limit": limit,
                                "remaining": 0,
                                "reset": int(oldest_time + window_seconds),
                                "window": window_name,
                            }
                        )

                        return True, limit_info

                # Update limit info for headers
                if window_name == "minute":  # Use minute window for headers
                    limit_info.update(
                        {
                            "limit": limit,
                            "remaining": max(0, limit - count),
                            "reset": int(current_time + window_seconds),
                        }
                    )

            # Not rate limited - record this request
            request_id = f"{current_time}:{id(identifier)}"

            # Add to all relevant windows
            for window_name, (window_seconds, limit) in windows.items():
                if limit > 0:
                    key = self._get_key(identifier, window_name)
                    await redis_client.zadd(key, {request_id: current_time})
                    await redis_client.expire(key, window_seconds + 60)  # Extra buffer

            return False, limit_info

        except Exception as exc:
            # Redis error — mark unavailable and fall back to in-memory
            logger.warning("Redis rate-limit error, falling back to in-memory: %s", exc)
            try:
                from app.core.redis import redis_manager
                redis_manager.mark_unavailable(str(exc))
            except Exception:
                pass
            per_min = limits.get("per_minute", 60)
            return _fallback_limiter.is_rate_limited(identifier, per_min)

    async def get_usage(self, identifier: str) -> dict:
        """
        Get current usage for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            dict: Usage statistics
        """
        redis_client = self._get_redis()
        if redis_client is None:
            return {"minute": 0, "hour": 0, "day": 0, "source": "unavailable"}

        current_time = time.time()
        usage = {}
        windows = {"minute": 60, "hour": 3600, "day": 86400}

        try:
            for window_name, window_seconds in windows.items():
                key = self._get_key(identifier, window_name)
                cutoff_time = current_time - window_seconds
                await redis_client.zremrangebyscore(key, "-inf", cutoff_time)
                count = await redis_client.zcard(key)
                usage[window_name] = count
        except Exception:
            return {"minute": 0, "hour": 0, "day": 0, "source": "error"}

        return usage

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            bool: True if reset successful
        """
        redis_client = self._get_redis()
        if redis_client is None:
            return False

        windows = ["minute", "hour", "day"]
        try:
            for window in windows:
                key = self._get_key(identifier, window)
                await redis_client.delete(key)
        except Exception:
            return False

        return True


# ==================== Middleware ====================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    Checks rate limits before processing requests.
    """

    def __init__(self, app: ASGIApp, redis_client: Optional[aioredis.Redis] = None, enabled: bool = True):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
        self.enabled = enabled and settings.RATE_LIMIT_ENABLED

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.
        Prioritizes: API key > User ID > IP address

        Args:
            request: FastAPI request

        Returns:
            str: Unique identifier
        """
        # Check for API key in header
        api_key = request.headers.get(settings.API_KEY_HEADER_NAME)
        if api_key:
            return f"apikey:{api_key[:16]}"  # Use prefix for identification

        # Check for authenticated user (if using session/JWT)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        # Check for proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _get_limits(self, request: Request) -> dict:
        """
        Get rate limits for request.

        Args:
            request: FastAPI request

        Returns:
            dict: Rate limits
        """
        # Check if API key is present (higher limits)
        if request.headers.get(settings.API_KEY_HEADER_NAME):
            return {
                "per_minute": settings.API_KEY_RATE_LIMIT_PER_MINUTE,
                "per_hour": settings.API_KEY_RATE_LIMIT_PER_HOUR,
                "per_day": settings.API_KEY_RATE_LIMIT_PER_DAY,
            }

        # Default limits (unauthenticated)
        return {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.RATE_LIMIT_PER_HOUR,
            "per_day": settings.RATE_LIMIT_PER_DAY,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            Response: HTTP response
        """
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get identifier and limits
        identifier = self._get_identifier(request)
        limits = self._get_limits(request)

        # Check rate limit
        is_limited, limit_info = await self.limiter.is_rate_limited(
            identifier, limits, burst_allowance=settings.RATE_LIMIT_BURST
        )

        # Add rate limit headers
        response_headers = {
            "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(limit_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(limit_info.get("reset", 0)),
        }

        if is_limited:
            # Return 429 Too Many Requests
            response_headers["Retry-After"] = str(limit_info["retry_after"])

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Please try again in {limit_info['retry_after']} seconds.",
                    "retry_after": limit_info["retry_after"],
                    "limit": limit_info["limit"],
                    "window": limit_info["window"],
                },
                headers=response_headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for header, value in response_headers.items():
            response.headers[header] = value

        return response


# ==================== Decorator for Route-Specific Limits ====================


def rate_limit(
    per_minute: Optional[int] = None, per_hour: Optional[int] = None, per_day: Optional[int] = None
):
    """
    Decorator for route-specific rate limits.

    Args:
        per_minute: Requests per minute
        per_hour: Requests per hour
        per_day: Requests per day

    Usage:
        @router.post("/expensive-endpoint")
        @rate_limit(per_minute=5, per_hour=20)
        async def expensive_endpoint():
            ...
    """

    def decorator(func):
        func._rate_limit = {"per_minute": per_minute, "per_hour": per_hour, "per_day": per_day}
        return func

    return decorator
