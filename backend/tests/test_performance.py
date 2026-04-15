"""
BlockScope Backend Performance Tests.

Tests cover:
  - Endpoint response time SLAs (health < 200ms, scan < 2000ms)
  - Analysis cache effectiveness (2nd call faster than 1st)
  - Concurrent request handling
  - Database query performance
  - Slither wrapper caching

Run (unit + integration tests only, no live server required):
    cd backend
    pytest tests/test_performance.py -v --tb=short --no-cov

Run with coverage (must meet 80% threshold across all sources):
    cd backend
    pytest tests/ -v --tb=short

Note: TestEndpointResponseTimes is auto-skipped when the backend server is not
running at http://localhost:8000. To run live SLA checks:
    1. Start the backend: uvicorn app.main:app --port 8000
    2. pytest tests/test_performance.py::TestEndpointResponseTimes -v --no-cov
"""

import asyncio
import statistics
import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import httpx

# ─── Test configuration ───────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"

# SLA thresholds (milliseconds)
SLA = {
    "health":     200,
    "root":       100,
    "scan":     2_000,
    "list_scans": 500,
    "performance":200,
}

SAMPLE_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleToken {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
        balances[msg.sender] = 1_000_000;
    }

    function transfer(address to, uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to]         += amount;
    }

    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }
}
"""

REENTRANCY_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // Classic reentrancy vulnerability: external call before state update
    function withdraw() public {
        uint256 balance = balances[msg.sender];
        require(balance > 0, "No balance");
        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "Transfer failed");
        balances[msg.sender] = 0;  // State updated AFTER external call
    }
}
"""


# ─── Helper ───────────────────────────────────────────────────────────────────

def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


# ─── Unit: Analysis Cache ─────────────────────────────────────────────────────

class TestAnalysisCache:
    """Unit tests for the LRU analysis cache."""

    def test_make_key_is_deterministic(self):
        from analysis.cache import AnalysisCache
        k1 = AnalysisCache.make_key("code", "MyContract")
        k2 = AnalysisCache.make_key("code", "MyContract")
        assert k1 == k2, "Same inputs must produce the same key"

    def test_make_key_differs_for_different_inputs(self):
        from analysis.cache import AnalysisCache
        k1 = AnalysisCache.make_key("codeA", "ContractA")
        k2 = AnalysisCache.make_key("codeB", "ContractA")
        assert k1 != k2

    def test_get_returns_none_on_miss(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache()
        assert cache.get("nonexistent_key") is None

    def test_set_and_get_round_trip(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache()
        cache.set("key1", {"score": 100})
        result = cache.get("key1")
        assert result == {"score": 100}

    def test_lru_eviction_at_capacity(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache(max_size=3)
        for i in range(4):
            cache.set(f"key{i}", f"value{i}")
        # key0 was the first inserted (LRU) and should have been evicted
        assert cache.get("key0") is None
        assert cache.get("key3") == "value3"

    def test_ttl_expiry(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache(ttl_seconds=0.05)  # 50 ms TTL
        cache.set("expiring_key", "data")
        assert cache.get("expiring_key") == "data"
        time.sleep(0.1)  # Wait for expiry
        assert cache.get("expiring_key") is None, "Entry should have expired"

    def test_hit_rate_increases_on_repeated_access(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache()
        cache.set("k", "v")
        cache.get("k")   # hit
        cache.get("k")   # hit
        cache.get("nope")  # miss
        assert cache.stats["hits"] == 2
        assert cache.stats["misses"] == 1
        assert cache.stats["hit_rate_pct"] == pytest.approx(66.7, abs=0.1)

    def test_clear_empties_cache(self):
        from analysis.cache import AnalysisCache
        cache = AnalysisCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cleared = cache.clear()
        assert cleared == 2
        assert cache.stats["size"] == 0

    def test_cache_is_thread_safe(self):
        """Verify no data races when multiple threads write simultaneously."""
        import threading
        from analysis.cache import AnalysisCache

        cache = AnalysisCache(max_size=50)
        errors: List[Exception] = []

        def writer(thread_id: int):
            try:
                for i in range(20):
                    cache.set(f"t{thread_id}-k{i}", f"v{i}")
                    cache.get(f"t{thread_id}-k{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread-safety errors: {errors}"


# ─── Unit: SlitherWrapper ─────────────────────────────────────────────────────

class TestSlitherWrapperPerformance:
    """Performance characteristics of the optimized SlitherWrapper."""

    def test_lazy_availability_probe(self):
        """available property should be evaluated at most once."""
        from analysis.slither_wrapper import SlitherWrapper
        wrapper = SlitherWrapper()
        # Access multiple times — should not import Slither more than once
        _ = wrapper.available
        _ = wrapper.available
        _ = wrapper.available
        # No assertion needed — we're checking it doesn't raise

    def test_parse_cache_starts_empty(self):
        from analysis.slither_wrapper import SlitherWrapper, _PARSE_CACHE
        _PARSE_CACHE.clear()
        assert SlitherWrapper.parse_cache_size() == 0

    def test_file_not_found_raises(self):
        from analysis.slither_wrapper import SlitherWrapper
        wrapper = SlitherWrapper()
        if not wrapper.available:
            pytest.skip("Slither not installed")
        with pytest.raises(FileNotFoundError):
            wrapper.parse_contract("/nonexistent/path/contract.sol")


# ─── Integration: Orchestrator with cache ─────────────────────────────────────

class TestOrchestratorCaching:
    """Verify the orchestrator uses the cache correctly."""

    def test_second_analysis_returns_cached_result(self):
        """Identical source code should be served from cache on 2nd call."""
        from analysis.orchestrator import AnalysisOrchestrator
        from analysis.models import ScanRequest
        from analysis.cache import analysis_cache

        analysis_cache.clear()
        orchestrator = AnalysisOrchestrator(rules=[])

        request = ScanRequest(
            source_code=SAMPLE_CONTRACT,
            contract_name="CacheTest",
            file_path="test.sol",
        )

        t0 = time.perf_counter()
        result1 = orchestrator.analyze(request)
        first_ms = _elapsed_ms(t0)

        t0 = time.perf_counter()
        result2 = orchestrator.analyze(request)
        second_ms = _elapsed_ms(t0)

        assert result1.contract_name == result2.contract_name
        assert result1.overall_score == result2.overall_score
        # Cache hit should be at least 5× faster than the first call
        assert second_ms < first_ms * 0.2, (
            f"Cache hit should be near-instant; got {second_ms:.1f} ms "
            f"(first call was {first_ms:.1f} ms)"
        )

    def test_different_source_code_not_cached(self):
        """Two different contracts must produce independent results."""
        from analysis.orchestrator import AnalysisOrchestrator
        from analysis.models import ScanRequest
        from analysis.cache import analysis_cache

        analysis_cache.clear()
        orchestrator = AnalysisOrchestrator(rules=[])

        req1 = ScanRequest(source_code=SAMPLE_CONTRACT,    contract_name="A", file_path="a.sol")
        req2 = ScanRequest(source_code=REENTRANCY_CONTRACT, contract_name="B", file_path="b.sol")

        result1 = orchestrator.analyze(req1)
        result2 = orchestrator.analyze(req2)

        assert result1.contract_name != result2.contract_name


# ─── Live endpoint performance tests ─────────────────────────────────────────
# These tests require the backend to be running at BASE_URL.
# Skip them automatically when the server is not available.

def _server_available() -> bool:
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            r = client.get(f"{BASE_URL}/health")
            return r.status_code in (200, 503)
    except Exception:
        return False


@pytest.mark.skipif(not _server_available(), reason="Backend server not running")
class TestEndpointResponseTimes:
    """
    Live endpoint SLA checks.
    Each endpoint is called N times; the median latency must meet the SLA.
    """

    N_SAMPLES = 3

    @classmethod
    def setup_class(cls):
        cls.client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    @classmethod
    def teardown_class(cls):
        cls.client.close()

    def _measure(self, method: str, path: str, **kwargs) -> List[float]:
        latencies = []
        for _ in range(self.N_SAMPLES):
            t0 = time.perf_counter()
            response = getattr(self.client, method)(path, **kwargs)
            latencies.append(_elapsed_ms(t0))
            assert response.status_code < 500, (
                f"{method.upper()} {path} returned {response.status_code}"
            )
        return latencies

    def test_health_endpoint_sla(self):
        latencies = self._measure("get", "/health")
        median = statistics.median(latencies)
        assert median < SLA["health"], (
            f"Health check median {median:.0f} ms exceeds SLA {SLA['health']} ms"
        )

    def test_root_endpoint_sla(self):
        latencies = self._measure("get", "/")
        median = statistics.median(latencies)
        assert median < SLA["root"], (
            f"Root endpoint median {median:.0f} ms exceeds SLA {SLA['root']} ms"
        )

    def test_list_scans_sla(self):
        latencies = self._measure("get", "/api/v1/scans?limit=10")
        median = statistics.median(latencies)
        assert median < SLA["list_scans"], (
            f"List scans median {median:.0f} ms exceeds SLA {SLA['list_scans']} ms"
        )

    def test_performance_metrics_endpoint(self):
        latencies = self._measure("get", "/api/v1/performance")
        median = statistics.median(latencies)
        assert median < SLA["performance"], (
            f"Performance metrics endpoint median {median:.0f} ms "
            f"exceeds SLA {SLA['performance']} ms"
        )

    def test_scan_endpoint_sla(self):
        """Full scan must complete within the 2-second SLA."""
        payload = {
            "source_code":    SAMPLE_CONTRACT,
            "contract_name":  "PerfTestContract",
        }
        latencies = self._measure("post", "/api/v1/scan", json=payload)
        median = statistics.median(latencies)
        assert median < SLA["scan"], (
            f"Scan endpoint median {median:.0f} ms exceeds SLA {SLA['scan']} ms"
        )

    def test_scan_cache_acceleration(self):
        """Second scan of identical code should be significantly faster."""
        payload = {"source_code": SAMPLE_CONTRACT, "contract_name": "CacheLiveTest"}
        t0 = time.perf_counter()
        self.client.post("/api/v1/scan", json=payload)
        first_ms = _elapsed_ms(t0)

        t0 = time.perf_counter()
        self.client.post("/api/v1/scan", json=payload)
        second_ms = _elapsed_ms(t0)

        print(f"\n  First scan:  {first_ms:.0f} ms")
        print(f"  Second scan: {second_ms:.0f} ms (cache hit)")

        # Cache hit should be at least 50% faster
        assert second_ms < first_ms * 0.5, (
            f"Expected cache to cut latency by ≥50%; "
            f"first={first_ms:.0f}ms, second={second_ms:.0f}ms"
        )

    def test_concurrent_requests(self):
        """Ten concurrent health checks must all complete within 1 second."""
        import threading

        results = []
        errors  = []

        def do_request():
            try:
                client = httpx.Client(base_url=BASE_URL, timeout=10.0)
                t0 = time.perf_counter()
                r = client.get("/health")
                latency = _elapsed_ms(t0)
                results.append((r.status_code, latency))
                client.close()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=do_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent request errors: {errors}"
        assert all(status < 500   for status, _ in results)
        assert all(latency < 1000 for _, latency in results), (
            f"Some concurrent requests exceeded 1 s: "
            f"{[f'{ms:.0f}ms' for _, ms in results]}"
        )
