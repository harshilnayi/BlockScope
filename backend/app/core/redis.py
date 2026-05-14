"""
BlockScope Centralized Redis Manager.

Provides a single async Redis connection pool shared by all consumers
(scan result caching, rate limiting, health checks).  The manager
tracks connection health so consumers can gracefully degrade when
Redis is unreachable.

Usage::

    from app.core.redis import redis_manager

    # In lifespan startup:
    await redis_manager.connect()

    # In application code:
    if redis_manager.is_available:
        await redis_manager.redis.set("key", "value")

    # In lifespan shutdown:
    await redis_manager.disconnect()
"""

import asyncio
import logging
import time
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger("blockscope.redis")


class RedisManager:
    """
    Async Redis connection manager with health tracking.

    Features:
        - Single shared connection pool (module-level instance)
        - ``is_available`` flag for graceful degradation
        - ``mark_unavailable()`` for consumers to report errors
        - ``connection_status`` property for health endpoints
    """

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None
        self._available: bool = False
        self._last_error: Optional[str] = None
        self._last_check: float = 0.0
        self._connect_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        url: str = "redis://localhost:6379/0",
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ) -> bool:
        """
        Establish the Redis connection pool.

        Returns:
            ``True`` if the connection succeeded and PING was answered.
        """
        if self._redis is not None:
            return self._available

        try:
            self._redis = aioredis.from_url(
                url,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True,
            )
            # Verify connectivity
            await self._redis.ping()
            self._available = True
            self._last_error = None
            self._connect_time = time.time()
            logger.info("Redis connected: %s", _sanitize_url(url))
            return True

        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.warning("Redis connection failed — degrading gracefully: %s", exc)
            # Keep the client object so we can attempt reconnection later
            return False

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._redis is not None:
            try:
                await self._redis.close()
                logger.info("Redis disconnected")
            except Exception:
                pass
            finally:
                self._redis = None
                self._available = False
                self._connect_time = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """``True`` when Redis is connected and responsive."""
        return self._available and self._redis is not None

    @property
    def redis(self) -> aioredis.Redis:
        """
        Return the underlying Redis client.

        Raises:
            RuntimeError: If Redis is not connected.
        """
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    def mark_unavailable(self, error: str) -> None:
        """
        Mark Redis as unavailable after a consumer encounters an error.

        This prevents stale ``is_available`` between health checks.
        Consumers (cache, rate-limit) should call this in their
        ``except`` handlers when a Redis operation fails.

        Args:
            error: Description of the error that occurred.
        """
        self._available = False
        self._last_error = error
        self._last_check = time.time()
        logger.warning("Redis marked unavailable by consumer: %s", error)

    @property
    def connection_status(self) -> dict:
        """
        Return connection status for health endpoints.

        Use this instead of accessing private attributes directly.
        """
        return {
            "initialized": self._redis is not None,
            "available": self._available,
            "last_error": self._last_error,
        }

    async def ping(self) -> bool:
        """
        Check if Redis is responsive.

        Updates ``is_available`` as a side-effect.

        Returns:
            ``True`` if Redis answered PING.
        """
        if self._redis is None:
            self._available = False
            return False

        try:
            await asyncio.wait_for(self._redis.ping(), timeout=3.0)
            self._available = True
            self._last_error = None
            self._last_check = time.time()
            return True
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            self._last_check = time.time()
            return False

    async def health(self) -> dict:
        """
        Return a health-check dict for the ``/health`` endpoint.

        Returns:
            Dict with status, uptime, and error info.
        """
        is_up = await self.ping()
        result = {
            "status": "ok" if is_up else "error",
            "connected": is_up,
        }
        if self._connect_time and is_up:
            result["uptime_seconds"] = round(time.time() - self._connect_time, 1)
        if self._last_error:
            result["last_error"] = self._last_error
        return result

    @property
    def stats(self) -> dict:
        """Return connection stats for the performance endpoint."""
        return {
            "connected": self._available,
            "last_error": self._last_error,
            "uptime_seconds": (
                round(time.time() - self._connect_time, 1)
                if self._connect_time
                else None
            ),
        }


def _sanitize_url(url: str) -> str:
    """Mask password in Redis URL for logging."""
    if "@" in url:
        prefix, host = url.rsplit("@", 1)
        scheme = prefix.split("://")[0] if "://" in prefix else "redis"
        return f"{scheme}://***@{host}"
    return url


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
redis_manager = RedisManager()
"""Global Redis manager instance — import and use throughout the application."""
