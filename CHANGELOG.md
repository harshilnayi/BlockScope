# Changelog

All notable changes to BlockScope will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-20

### Added

#### Core Analysis Engine
- ML-powered smart contract vulnerability detection with confidence scoring
- Slither static analysis integration with timeout protection and subprocess isolation
- Rule-based pattern matching for common vulnerability classes (reentrancy, overflow, access control)
- SHA-256 content-addressed analysis caching (LRU, 512 entries, 30-min TTL)
- Concurrent scan execution via bounded thread pool (4 workers)

#### REST API
- `POST /api/v1/scan/file` — upload and analyze Solidity contracts
- `GET /api/v1/scans` — paginated scan history with filtering
- `GET /api/v1/scans/{id}` — individual scan results with findings
- `GET /api/v1/performance` — cache stats, pool info, system metrics
- `GET /health` — deep health check (DB + Redis connectivity)
- `DELETE /admin/cache` — admin cache eviction endpoint

#### Authentication & Authorization
- JWT-based authentication (HS256, configurable expiry)
- API key authentication via `X-API-Key` header
- SHA-256 hashed API key storage (raw key shown once)
- Tier-based rate limiting (free / basic / premium / enterprise)
- Admin role with separate password-based access

#### Database
- PostgreSQL 15 with SQLAlchemy ORM
- Alembic migration system with indexed columns
- Optimized queries with pagination helpers (`paginate`, `get_by_id`)
- Connection pooling with `pool_pre_ping` health checks
- Transactional integrity for scan result persistence

#### Redis Integration
- Centralized Redis manager with connection pooling
- Two-tier caching (in-memory LRU + Redis distributed cache)
- Sliding-window rate limiting with Redis-backed counters
- Graceful degradation when Redis is unavailable
- Rate limit headers on all responses (`X-RateLimit-*`)

#### Frontend
- React SPA with Vite build system
- Code splitting via `React.lazy` + `Suspense`
- Manual Vite chunk splitting (App 31.9 kB, react-vendor 192.9 kB gzip)
- Service worker with cache-first shell strategy
- PWA manifest for installable experience
- Web Vitals monitoring (CLS, FID, FCP, LCP, TTFB)

#### Monitoring & Observability
- Prometheus metrics endpoint with Grafana dashboard
- Structured JSON logging with rotating file handler
- `PerformanceTimer` context manager for operation profiling
- GZip response compression middleware

#### Documentation
- API reference (`API_DOCUMENTATION.md`)
- Architecture guide (`ARCHITECTURE.md`)
- Deployment guide (`DEPLOYMENT.md`)
- User guide (`USER_GUIDE.md`)
- Troubleshooting guide (`TROUBLESHOOTING.md`)
- Contributing guidelines (`CONTRIBUTING.md`)
- Code of Conduct

### Security
- OWASP security headers on all responses (CSP, HSTS, X-Frame-Options, etc.)
- Input validation for file uploads (size, extension, MIME type, content)
- SQL injection prevention via SQLAlchemy parameterized queries
- Path traversal prevention on file operations
- Pre-commit hooks: `detect-private-key`, `detect-secrets`, `bandit`, `check-added-large-files`
- Docker credential externalization (no hardcoded passwords)
- Security policy with responsible disclosure process (`SECURITY.md`)

### Infrastructure
- Docker Compose development stack (PostgreSQL, Redis, backend, frontend)
- Docker Compose production configuration with resource limits
- Backend dev Dockerfile with hot-reload
- Frontend dev Dockerfile with HMR
- GitHub Actions CI/CD pipeline (`backend-ci.yml`)
- Prometheus + Grafana monitoring stack (`docker-compose.monitoring.yml`)

### Testing
- 320+ unit and integration tests across 22 test files
- Edge case and boundary testing (`test_edge_cases.py`)
- Security testing (`test_security.py`)
- Memory leak detection suite (`test_memory_leak.py`)
- Performance profiling tests (`test_performance.py`)
- End-to-end scan flow tests (`test_e2e.py`)
- Locust load testing configuration (1 / 10 / 50 concurrent users)
- Database integration tests with transactional rollback

### Fixed
- Resolved 15 pre-existing test failures:
  - Added `app_instance` fixture alias for backward compatibility
  - Fixed `@property` monkeypatch on `SlitherWrapper.available`
  - Eliminated parse cache cross-test pollution via `clear_parse_cache()`
- Hardened Docker Compose credentials (env-var references replace hardcoded values)
