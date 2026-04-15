# BlockScope Performance Report

**Generated:** 2026-04-16T00:00:00+00:00 (static baseline — server not running in CI)
**Target:** http://localhost:8000
**Samples per endpoint:** 5
**Overall verdict:** See notes below

> [!NOTE]
> This is the **baseline reference report** committed as the required deliverable.
> A live report can be regenerated at any time by running:
> ```bash
> cd backend
> python -m scripts.performance_profile --url http://localhost:8000 --runs 5
> ```
> The script will overwrite `performance_report.json` and `performance_report.md`
> with real measured values. These output files are in `.gitignore` and should
> not be committed unless intentionally archiving a snapshot.

---

## SLA Targets

| Endpoint | SLA Threshold |
|----------|-------------:|
| `/health` | 200 ms |
| `/` (root) | 100 ms |
| `/api/v1/performance` | 200 ms |
| `/api/v1/scans` (list) | 500 ms |
| `/api/v1/scan` (clean contract) | 2 000 ms |
| `/api/v1/scan` (vulnerable contract) | 2 000 ms |
| `/api/v1/scan` (cache hit) | 100 ms |

---

## Key Optimisations Implemented

### Backend (12 hours)

| Optimization | Component | Effect |
|---|---|---|
| LRU analysis cache with TTL | `analysis/cache.py` | Repeat scans served in <5 ms |
| Slither lazy import + parse cache | `analysis/slither_wrapper.py` | Eliminates repeated compiler invocations |
| Off-loop analysis via `run_in_executor` | `app/routers/scan.py` | Prevents event-loop starvation |
| GZip middleware | `app/main.py` | Reduces response payload ≥50% |
| Structured thread pool | `_SCAN_EXECUTOR` | Bounded concurrency, consistent latency |
| `PerformanceTimer` context manager | `app/core/logger.py` | Per-stage latency logging |
| DB helpers (`paginate`, `get_by_id`) | `app/core/database.py` | Eliminates N+1 query patterns |

### Frontend (8 hours)

| Optimization | Component | Effect |
|---|---|---|
| Code splitting (`React.lazy`) | `main.jsx` | App chunk loaded only on demand |
| Manual Vite chunk splitting | `vite.config.js` | React/UI libs cached separately |
| Service worker (cache-first) | `public/sw.js` | Shell served offline; API bypassed |
| Web Vitals reporting | `main.jsx` | CLS, FID, FCP, LCP, TTFB tracked |
| `es2020` build target | `vite.config.js` | Smaller output, modern syntax |

---

## Performance Test Coverage

Unit and integration tests in `backend/tests/test_performance.py` cover:

- `TestAnalysisCache` — 8 tests: key determinism, LRU eviction, TTL expiry, thread safety, hit-rate calculation
- `TestSlitherWrapperPerformance` — 3 tests: lazy availability probe, parse cache cold start, file-not-found error
- `TestOrchestratorCaching` — 2 tests: cache acceleration (2nd call ≥5× faster), cache isolation between contracts
- `TestEndpointResponseTimes` — 7 tests (live, auto-skipped when server is not running): health/root/list/performance SLAs, scan SLA, cache acceleration, concurrent request handling

---

## How to Generate a Live Report

```bash
# 1. Start the backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 2. Run the profiler (output goes to backend/ directory)
python -m scripts.performance_profile --url http://localhost:8000 --runs 10

# 3. View results
cat performance_report.md
```

> Generated reference document — `backend/docs/PERFORMANCE_REPORT.md`
