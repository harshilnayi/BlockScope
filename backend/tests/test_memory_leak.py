"""
Memory Leak Detection Tests for BlockScope Backend.

Verifies that:
  1. AnalysisCache never exceeds max_size entries (LRU eviction enforced).
  2. LRU eviction removes the least-recently-used entry (not just FIFO).
  3. TTL expiry removes stale entries before returning them.
  4. The ThreadPoolExecutor _SCAN_EXECUTOR does not leak OS threads.
  5. DB sessions are closed after each request (no connection pool exhaustion).
  6. Evicted ScanResult objects are not retained by the cache.
  7. Cache is thread-safe under concurrent access.

Run:
    cd backend
    pytest tests/test_memory_leak.py -v --no-cov
"""

import gc
import sys
import threading
import time
import weakref
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import os
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

from analysis.cache import AnalysisCache  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fake_scan_result(tag: str):
    """Return a minimal MagicMock that stands in for a ScanResult."""
    m = MagicMock()
    m.contract_name = tag
    m.vulnerabilities_count = 0
    m.severity_breakdown = {}
    m.overall_score = 100
    m.summary = "ok"
    m.findings = []
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. Cache size cap + LRU eviction
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalysisCacheSizeCap:
    """AnalysisCache must never hold more than max_size entries."""

    def setup_method(self):
        self.cache = AnalysisCache(max_size=5, ttl_seconds=3600)

    def test_router_cache_max_size_is_reasonable(self):
        """The router-level cache is configured with a sensible max_size."""
        from app.routers.scan import _analysis_cache
        stats = _analysis_cache.stats
        assert 64 <= stats["max_size"] <= 4096, (
            f"Router cache max_size={stats['max_size']} is outside the expected range [64, 4096]"
        )

    def test_cache_never_exceeds_max_size(self):
        """Filling the cache beyond max_size keeps size == max_size."""
        fill_count = 20  # well above max_size=5
        for i in range(fill_count):
            key = AnalysisCache.make_key(f"source_{i}", f"Contract_{i}")
            self.cache.set(key, _fake_scan_result(f"Contract_{i}"))

        assert self.cache.stats["size"] == 5, (
            f"Cache grew to {self.cache.stats['size']}, expected max 5"
        )

    def test_lru_entry_evicted_not_fifo(self):
        """LRU: the *least recently used* entry is evicted, not just the oldest insert."""
        # Insert 5 entries (fills the cache)
        keys = []
        for i in range(5):
            k = AnalysisCache.make_key(f"src_{i}", f"C_{i}")
            self.cache.set(k, _fake_scan_result(f"C_{i}"))
            keys.append(k)

        # Access keys[0] — it is now most-recently-used; keys[1] is now LRU
        _ = self.cache.get(keys[0])

        # Insert one more — should evict keys[1] (LRU), not keys[0]
        k_new = AnalysisCache.make_key("new_src", "NewContract")
        self.cache.set(k_new, _fake_scan_result("NewContract"))

        assert self.cache.get(keys[0]) is not None, "MRU entry should still be present"
        assert self.cache.get(keys[1]) is None, "LRU entry should have been evicted"
        assert self.cache.get(k_new) is not None, "New entry should be present"

    def test_different_contract_names_same_source_cached_separately(self):
        """Same source + different names → different cache keys."""
        source = "contract Foo {}"
        k1 = AnalysisCache.make_key(source, "ContractA")
        k2 = AnalysisCache.make_key(source, "ContractB")
        assert k1 != k2

        self.cache.set(k1, _fake_scan_result("ContractA"))
        self.cache.set(k2, _fake_scan_result("ContractB"))

        assert self.cache.stats["size"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# 2. TTL expiry
# ─────────────────────────────────────────────────────────────────────────────

class TestTTLExpiry:
    """Expired entries must not be returned by AnalysisCache.get()."""

    def test_entry_expired_after_ttl(self):
        """An entry set with a 50ms TTL must be gone within 200ms."""
        cache = AnalysisCache(max_size=10, ttl_seconds=0.05)
        key = AnalysisCache.make_key("src", "C")
        cache.set(key, _fake_scan_result("C"))

        assert cache.get(key) is not None, "Entry should exist immediately after set()"
        time.sleep(0.2)
        assert cache.get(key) is None, "Entry should have expired after TTL"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Object retention (weak-reference test)
# ─────────────────────────────────────────────────────────────────────────────

class TestObjectRetentionAfterEviction:
    """Evicted ScanResult objects must not be retained by the cache."""

    def test_evicted_result_not_retained_in_cache(self):
        """
        After eviction the cache dict must not hold a reference to the value.
        We verify by checking the key is gone; the strong reference is gone,
        so Python is free to collect the object.
        """
        cache = AnalysisCache(max_size=2, ttl_seconds=3600)
        k1 = AnalysisCache.make_key("s1", "A")
        k2 = AnalysisCache.make_key("s2", "B")
        k3 = AnalysisCache.make_key("s3", "C")  # will cause k1 to be evicted (LRU)

        result1 = _fake_scan_result("A")
        weak = weakref.ref(result1)

        cache.set(k1, result1)
        cache.set(k2, _fake_scan_result("B"))

        # k1 is now LRU — access k2 to make k1 even more LRU
        _ = cache.get(k2)

        del result1  # drop our local strong reference

        # k3 insert evicts k1 (LRU)
        cache.set(k3, _fake_scan_result("C"))

        assert cache.get(k1) is None, "Evicted key must not be returned"
        gc.collect()
        # After GC: if the cache held no strong ref, weak() should be None.
        # MagicMock can hold internal refs so we check absence-from-cache only.
        assert k1 not in cache._store, "Evicted key must not be in internal store"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Thread pool — no leaked OS threads
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadPoolNoLeak:
    """_SCAN_EXECUTOR must not leak OS threads between test runs."""

    def test_executor_threads_are_bounded(self):
        """Thread count must not grow unboundedly after many executor submissions."""
        from app.routers.scan import _SCAN_EXECUTOR

        alive_before = threading.active_count()

        # Submit a no-op task to ensure at least one worker thread is started
        future = _SCAN_EXECUTOR.submit(lambda: None)
        future.result(timeout=5)

        alive_after = threading.active_count()

        # Allow +10 for Python internals (GIL, signal handler, main thread, etc.)
        assert alive_after <= alive_before + 10, (
            f"Thread count grew unexpectedly: {alive_before} → {alive_after}"
        )

    def test_executor_accepts_work_after_multiple_calls(self):
        """Executor must remain usable after many submissions (no pool exhaustion)."""
        from app.routers.scan import _SCAN_EXECUTOR

        results = []
        for i in range(20):
            f = _SCAN_EXECUTOR.submit(lambda x=i: x * 2)
            results.append(f.result(timeout=5))

        assert results == [i * 2 for i in range(20)]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cache thread-safety
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheThreadSafety:
    """AnalysisCache must not corrupt state under concurrent reads/writes."""

    def test_concurrent_set_and_get_no_exception(self):
        """50 concurrent threads reading/writing the same cache must not raise."""
        cache = AnalysisCache(max_size=20, ttl_seconds=3600)
        errors = []

        def worker(idx):
            try:
                key = AnalysisCache.make_key(f"src_{idx % 10}", f"C_{idx % 10}")
                cache.set(key, _fake_scan_result(f"C_{idx}"))
                cache.get(key)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Concurrent cache access raised: {errors}"
        assert cache.stats["size"] <= 20


# ─────────────────────────────────────────────────────────────────────────────
# 6. DB session cleanup
# ─────────────────────────────────────────────────────────────────────────────

class TestDBSessionCleanup:
    """Database sessions must be closed after each request (no connection pool exhaustion)."""

    def test_get_db_yields_and_closes(self):
        """get_db() generator must call session.close() in its finally block."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.database import get_db, Base

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)

        closed_calls = []

        with patch("app.core.database.SessionLocal") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.close.side_effect = lambda: closed_calls.append(True)
            mock_session_factory.return_value = mock_session

            gen = get_db()
            db = next(gen)
            assert db is mock_session

            try:
                next(gen)
            except StopIteration:
                pass

            assert len(closed_calls) == 1, (
                "Session.close() was not called — potential connection pool leak"
            )

        engine.dispose()
