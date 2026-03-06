"""
BlockScope Rate Limiting Middleware
Implements sliding window rate limiting with Redis
"""

import time
from typing import Callable, Optional

import redis.asyncio as aioredis
from app.core.config import settings
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ==================== Redis Connection ====================


class RateLimitRedis:
    """Redis connection manager for rate limiting"""

    _instance = None
    _redis: Optional[aioredis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self):
        """Establish Redis connection"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url_str,
                password=settings.REDIS_PASSWORD,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
            )

    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def redis(self) -> aioredis.Redis:
        """Get Redis client"""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis


rate_limit_redis = RateLimitRedis()


# ==================== Rate Limiting Logic ====================


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Implements token bucket algorithm with Redis sorted sets.
    """

    def __init__(self, redis_client: aioredis.Redis, prefix: str = "ratelimit"):
        self.redis = redis_client
        self.prefix = prefix

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

        Args:
            identifier: Unique identifier
            limits: Rate limits dict {per_minute, per_hour, per_day}
            burst_allowance: Allow burst requests beyond limit

        Returns:
            tuple: (is_limited, limit_info)
                - is_limited: True if should be rate limited
                - limit_info: Dict with limit details
        """
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

        for window_name, (window_seconds, limit) in windows.items():
            if limit == 0:  # Skip if limit not set
                continue

            key = self._get_key(identifier, window_name)

            # Use sorted set to track requests in time window
            # Score is timestamp, member is unique request ID

            # Remove old requests outside window
            cutoff_time = current_time - window_seconds
            await self.redis.zremrangebyscore(key, "-inf", cutoff_time)

            # Count requests in current window
            count = await self.redis.zcard(key)

            # Check if limit exceeded (with burst allowance)
            effective_limit = limit + burst_allowance

            if count >= effective_limit:
                # Rate limited!
                # Get oldest request to calculate retry_after
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
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
                await self.redis.zadd(key, {request_id: current_time})
                await self.redis.expire(key, window_seconds + 60)  # Extra buffer

        return False, limit_info

    async def get_usage(self, identifier: str) -> dict:
        """
        Get current usage for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            dict: Usage statistics
        """
        current_time = time.time()

        usage = {}
        windows = {"minute": 60, "hour": 3600, "day": 86400}

        for window_name, window_seconds in windows.items():
            key = self._get_key(identifier, window_name)

            # Remove old requests
            cutoff_time = current_time - window_seconds
            await self.redis.zremrangebyscore(key, "-inf", cutoff_time)

            # Count requests
            count = await self.redis.zcard(key)
            usage[window_name] = count

        return usage

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            bool: True if reset successful
        """
        windows = ["minute", "hour", "day"]

        for window in windows:
            key = self._get_key(identifier, window)
            await self.redis.delete(key)

        return True


# ==================== Middleware ====================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    Checks rate limits before processing requests.
    """

    def __init__(self, app: ASGIApp, redis_client: aioredis.Redis, enabled: bool = True):
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


# ==================== Usage Example ====================
"""
# In main.py:

from fastapi import FastAPI
from app.core.rate_limit import RateLimitMiddleware, rate_limit_redis

app = FastAPI()

@app.on_event("startup")
async def startup():
    await rate_limit_redis.connect()

    # Add middleware
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=rate_limit_redis.redis,
        enabled=True
    )

@app.on_event("shutdown")
async def shutdown():
    await rate_limit_redis.disconnect()


# In routes:

@router.post("/scan")
@rate_limit(per_minute=5, per_hour=20)  # Custom limits for this endpoint
async def scan_contract():
    ...
"""
