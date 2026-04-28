"""
BlockScope Analysis Cache.

Provides an in-memory LRU cache for contract analysis results to avoid
re-running expensive Slither + rule scans for identical source code.

Design:
  - Keyed by SHA-256 hash of (source_code, contract_name)
  - TTL-based expiry (default 30 minutes)
  - Configurable max-size (default 128 entries)
  - Thread-safe via threading.Lock
  - Hit/miss metrics exposed for observability
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger("blockscope.cache")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_MAX_SIZE: int = 512
_DEFAULT_TTL_SECONDS: float = 1_800.0  # 30 minutes


class _CacheEntry:
    """Internal cache slot with expiry tracking."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: object, ttl: float) -> None:
        self.value = value
        self.expires_at: float = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class AnalysisCache:
    """
    Thread-safe LRU cache for ScanResult objects.

    Usage::

        cache = AnalysisCache(max_size=128, ttl_seconds=1800)
        key = cache.make_key(source_code, contract_name)
        result = cache.get(key)
        if result is None:
            result = orchestrator.analyze(request)
            cache.set(key, result)
    """

    def __init__(
        self,
        max_size: int = _DEFAULT_MAX_SIZE,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(source_code: str, contract_name: str = "") -> str:
        """
        Build a deterministic cache key from source code + contract name.

        Args:
            source_code: Solidity source code string.
            contract_name: Optional contract name for disambiguation.

        Returns:
            Hex SHA-256 digest of the combined inputs.
        """
        payload = f"{contract_name}::{source_code}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[object]:
        """
        Return the cached value for *key*, or ``None`` on miss/expiry.

        Args:
            key: Cache key produced by :meth:`make_key`.

        Returns:
            Cached object, or ``None``.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._store[key]
                self._misses += 1
                logger.debug("Cache entry expired for key=%s…", key[:16])
                return None
            # Move to end (most-recently-used)
            self._store.move_to_end(key)
            self._hits += 1
            logger.debug("Cache hit for key=%s…", key[:16])
            return entry.value

    def set(self, key: str, value: object) -> None:
        """
        Store *value* under *key*, evicting the LRU entry if at capacity.

        Args:
            key: Cache key.
            value: Object to store (usually a ``ScanResult``).
        """
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = _CacheEntry(value, self._ttl)
            if len(self._store) > self._max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug("Cache evicted LRU key=%s…", evicted_key[:16])

    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from the cache.

        Args:
            key: Cache key to remove.

        Returns:
            ``True`` if the key existed, ``False`` otherwise.
        """
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> int:
        """
        Remove all entries from the cache.

        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info("Cache cleared (%d entries removed)", count)
            return count

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Return a snapshot of hit/miss/size metrics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = round(self._hits / total * 100, 1) if total else 0.0
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": hit_rate,
                "ttl_seconds": self._ttl,
            }

    def __repr__(self) -> str:
        s = self.stats
        return (
            f"AnalysisCache(size={s['size']}/{s['max_size']}, "
            f"hits={s['hits']}, misses={s['misses']}, "
            f"hit_rate={s['hit_rate_pct']}%)"
        )


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all requests
# ---------------------------------------------------------------------------
analysis_cache = AnalysisCache()
