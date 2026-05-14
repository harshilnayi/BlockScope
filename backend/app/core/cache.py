"""
BlockScope Redis Scan Cache (L2).

Provides a Redis-backed cache layer for ``ScanResult`` objects.
Works alongside the in-memory ``AnalysisCache`` (L1) to form a
two-tier caching strategy:

    L1 (in-memory, ~0µs)  →  L2 (Redis, ~1ms)  →  full analysis (~5s)

Design:
    - Keys: ``{prefix}{sha256_hex}`` — same SHA-256 key as the L1 cache
    - Values: JSON-serialized ``ScanResult`` dicts
    - TTL: configurable (default 24 hours)
    - Graceful degradation: returns ``None`` when Redis is unreachable
    - Statistics tracked for Prometheus / performance endpoint
"""

import json
import logging
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

logger = logging.getLogger("blockscope.cache.redis")


class RedisScanCache:
    """
    Redis-backed L2 cache for analysis results.

    Usage::

        from app.core.cache import redis_scan_cache

        # Store
        await redis_scan_cache.set(key, scan_result_dict)

        # Retrieve
        cached = await redis_scan_cache.get(key)

        # Stats
        stats = redis_scan_cache.stats
    """

    def __init__(
        self,
        prefix: str = "bsc:scan:",
        ttl_seconds: int = 86_400,  # 24 hours
    ) -> None:
        self._prefix = prefix
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0
        self._errors = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _key(self, cache_key: str) -> str:
        """Build the full Redis key from a cache hash."""
        return f"{self._prefix}{cache_key}"

    def _get_redis(self):
        """
        Get the Redis client from the global manager.

        Returns ``None`` if Redis is unavailable (graceful degradation).
        """
        try:
            from app.core.redis import redis_manager

            if not redis_manager.is_available:
                return None
            return redis_manager.redis
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached scan result from Redis.

        Args:
            cache_key: SHA-256 hex digest (from ``AnalysisCache.make_key``).

        Returns:
            Deserialized dict of the ``ScanResult``, or ``None`` on miss.
        """
        r = self._get_redis()
        if r is None:
            self._misses += 1
            return None

        try:
            raw = await r.get(self._key(cache_key))
            if raw is None:
                self._misses += 1
                logger.debug("Redis cache MISS for key=%s…", cache_key[:16])
                return None

            self._hits += 1
            logger.debug("Redis cache HIT for key=%s…", cache_key[:16])
            return json.loads(raw)

        except Exception as exc:
            self._errors += 1
            logger.warning("Redis cache GET failed: %s", exc)
            return None

    async def set(self, cache_key: str, scan_result: Any) -> bool:
        """
        Store a scan result in Redis with TTL.

        Args:
            cache_key: SHA-256 hex digest.
            scan_result: A ``ScanResult`` dataclass or dict.

        Returns:
            ``True`` if stored successfully.
        """
        r = self._get_redis()
        if r is None:
            return False

        try:
            # Convert dataclass to dict if needed
            if hasattr(scan_result, "__dataclass_fields__"):
                data = asdict(scan_result)
            elif hasattr(scan_result, "dict"):
                data = scan_result.dict()
            elif isinstance(scan_result, dict):
                data = scan_result
            else:
                data = vars(scan_result)

            # Serialize findings (they may contain non-serializable objects)
            serialized = json.dumps(data, default=str)
            await r.set(self._key(cache_key), serialized, ex=self._ttl)
            logger.debug(
                "Redis cache SET key=%s… (TTL=%ds, size=%d bytes)",
                cache_key[:16],
                self._ttl,
                len(serialized),
            )
            return True

        except Exception as exc:
            self._errors += 1
            logger.warning("Redis cache SET failed: %s", exc)
            return False

    async def invalidate(self, cache_key: str) -> bool:
        """
        Remove a specific key from the Redis cache.

        Args:
            cache_key: SHA-256 hex digest.

        Returns:
            ``True`` if the key existed and was removed.
        """
        r = self._get_redis()
        if r is None:
            return False

        try:
            deleted = await r.delete(self._key(cache_key))
            return deleted > 0
        except Exception as exc:
            self._errors += 1
            logger.warning("Redis cache INVALIDATE failed: %s", exc)
            return False

    async def clear(self) -> int:
        """
        Remove all scan cache entries from Redis.

        Uses SCAN to find matching keys — safe for production
        (no blocking ``KEYS *`` call).

        Returns:
            Number of keys deleted.
        """
        r = self._get_redis()
        if r is None:
            return 0

        try:
            pattern = f"{self._prefix}*"
            count = 0
            async for key in r.scan_iter(match=pattern, count=100):
                await r.delete(key)
                count += 1
            logger.info("Redis cache cleared: %d entries removed", count)
            return count
        except Exception as exc:
            self._errors += 1
            logger.warning("Redis cache CLEAR failed: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Return hit/miss/error statistics."""
        total = self._hits + self._misses
        hit_rate = round(self._hits / total * 100, 1) if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "hit_rate_pct": hit_rate,
            "ttl_seconds": self._ttl,
            "prefix": self._prefix,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
redis_scan_cache = RedisScanCache()
"""Global Redis scan cache instance."""
