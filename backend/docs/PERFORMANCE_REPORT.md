# BlockScope Performance Report

**Document type:** Reference baseline with measured load data  
**Last updated:** 2026-04-16  
**Author:** shanaysoni

> [!IMPORTANT]
> The SLA targets below apply to **single-user (serial) requests**.
> Load test data shows latency increases non-linearly under concurrency.
> See the [Load Test Results](#load-test-results) and [Honest SLA Assessment](#honest-sla-assessment) sections.

---

## How to Generate a Live Single-Request Report

```bash
# 1. Start the backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. In a new terminal, run the profiler
python -m scripts.performance_profile --url http://localhost:8000 --runs 10

# 3. The script produces:
#    backend/performance_report.json  (machine-readable)
#    backend/performance_report.md    (human-readable table)
```

---

## SLA Targets (Serial / Single-User)

| Endpoint | SLA Threshold | Notes |
|----------|-------------:|-------|
| `GET /health` | 200 ms | Simple DB ping |
| `GET /` (root) | 100 ms | Static dict |
| `GET /api/v1/performance` | 200 ms | Cache stats + pool info |
| `GET /api/v1/scans` (list, 10 items) | 500 ms | Paginated query |
| `POST /api/v1/scan` (first call) | 2 000 ms | Includes Slither analysis |
| `POST /api/v1/scan` (cache hit) | 100 ms | Analysis skipped; DB write only |

---

## Load Test Results (Measured — Locust)

Results are from **actual Locust executions** against the local FastAPI backend.  
Source: [`backend/tests/load/benchmarks.md`](../tests/load/benchmarks.md)

### Scenario 1 — 1 Concurrent User

| Contract | Median | p95 | Avg |
|----------|-------:|----:|----:|
| Small | 423 ms | 430 ms | 426 ms |
| Medium | 450 ms | 470 ms | 455 ms |
| Large | 432 ms | 430 ms | 432 ms |

✅ All within 2 000 ms SLA at single-user load.

### Scenario 2 — 10 Concurrent Users

| Contract | Median | p95 | Avg |
|----------|-------:|----:|----:|
| Small | 2 900 ms | 3 800 ms | 2 522 ms |
| Medium | 740 ms | 1 300 ms | 851 ms |
| Large | 2 000 ms | 4 100 ms | 2 424 ms |

⚠️ Small and large contracts **exceed the 2 000 ms SLA** at 10 concurrent users.  
Aggregated avg: **2 205 ms** · Failures: 0

### Scenario 3 — 50 Concurrent Users

| Contract | Median | p95 | Avg |
|----------|-------:|----:|----:|
| Small | 7 300 ms | 18 000 ms | 7 796 ms |
| Medium | 8 900 ms | 18 000 ms | 9 636 ms |
| Large | 7 000 ms | 12 000 ms | 6 823 ms |

❌ **All contracts exceed the 2 000 ms SLA** at 50 users.  
Aggregated avg: **8 260 ms** · Failures: 0 (stable under load, but slow)

---

## Honest SLA Assessment

| Deliverable | Status | Evidence |
|---|:-:|---|
| Backend response < 2 s (serial) | ✅ | 1-user Locust scenario: 423–450 ms |
| Backend response < 2 s (10 users) | ⚠️ | Small/large contracts: 2 900–4 100 ms p95 |
| Backend response < 2 s (50 users) | ❌ | Median 7 000–8 900 ms across all contracts |
| Cache acceleration | ✅ | Analysis cache hit skips Slither; DB persists ~5 ms |
| Frontend load < 1 s | ⚠️ | Build produces split bundles (App 31.9 kB gzip); no Lighthouse audit committed |
| System stability under load | ✅ | Zero failures across all 3 Locust scenarios |

---

## Bottleneck Analysis

The primary bottleneck is **Slither execution** — the Solidity compiler is invoked synchronously in an OS subprocess for each unique contract. This cannot be parallelised beyond the available CPU cores.

Implemented mitigations:
1. **Analysis result cache** (`_analysis_cache` in `scan.py`) — deduplicated Slither invocations by SHA-256 key. Cache hit serves from memory and only runs a DB insert (~5 ms).
2. **Bounded thread pool** (`_SCAN_EXECUTOR`, max 4 workers) — prevents event-loop starvation.
3. **GZip compression** — reduces response payload ≥50%.

Remaining work for high-concurrency:
- Queue-based scan processing (Celery / RQ) to decouple analysis from the HTTP request lifecycle
- Slither result serialisation + horizontal scaling

---

## Key Optimisations Implemented

### Backend

| Optimisation | Component | Status |
|---|---|:-:|
| LRU analysis cache with bounded size (512 entries max) | `app/routers/scan.py` | ✅ |
| SHA-256 cache key (source + contract name) | `app/routers/scan.py` | ✅ |
| DB row always inserted (no scan_id leakage) | `app/routers/scan.py` | ✅ |
| Off-loop analysis via `run_in_executor` | `app/routers/scan.py` | ✅ |
| GZip middleware | `app/main.py` | ✅ |
| PerformanceTimer context manager | `app/core/logger.py` | ✅ |
| DB helpers (`paginate`, `get_by_id`) | `app/core/database.py` | ✅ |
| Slither lazy import + parse cache | `analysis/slither_wrapper.py` | ✅ |

### Frontend

| Optimisation | Component | Status |
|---|---|:-:|
| Code splitting (`React.lazy` + `Suspense`) | `main.jsx` | ✅ |
| Manual Vite chunk splitting | `vite.config.js` | ✅ |
| Production build bundles (App 31.9 kB, react-vendor 192.9 kB) | `vite.config.js` | ✅ |
| Service worker (cache-first shell, network-only API) | `public/sw.js` | ✅ |
| PWA manifest | `public/manifest.json` | ✅ |
| Web Vitals (CLS, FID, FCP, LCP, TTFB) | `main.jsx` | ✅ |
| Lighthouse audit committed | — | ❌ Pending |

---

## Memory Leak Detection

**Detection test suite:** `backend/tests/test_memory_leak.py` — **8 passing tests**

Test classes:

| Test class | What it verifies |
|---|---|
| `TestAnalysisCacheSizeCap` | Cache never exceeds `_ANALYSIS_CACHE_MAX` (512); FIFO eviction order; no cross-contract key contamination |
| `TestObjectRetentionAfterEviction` | Evicted `ScanResult` objects are not retained by `_analysis_result_cache` (weak-reference check) |
| `TestThreadPoolNoLeak` | `_SCAN_EXECUTOR` thread count stays bounded after repeated submissions; pool remains usable |
| `TestDBSessionCleanup` | `get_db()` generator calls `session.close()` in its `finally` block every time |

Run:
```bash
cd backend
pytest tests/test_memory_leak.py -v --no-cov
# Expected: 8 passed in ~2s
```

Long-running mitigation: `_analysis_cache` is capped at **512 entries** with LRU eviction and a 30-minute TTL.
For implementation details see the `AnalysisCache` class in `analysis/cache.py`.

---

## Frontend Performance Audit

See `frontend/docs/LIGHTHOUSE_AUDIT.md` for:
- Full bundle size analysis (measured from `npm run build`)
- Implementation checklist with file references  
- Estimated Lighthouse score ranges (Performance 85–95, A11y 90–100)
- Frontend load < 1 s analysis (16 kB first-paint gzip, ~600 ms FCP estimate)

---

*Document last updated: 2026-04-16 — `backend/docs/PERFORMANCE_REPORT.md`*
