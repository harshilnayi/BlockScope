# BlockScope — Troubleshooting Guide

> Common issues and solutions for BlockScope development and deployment

---

## Table of Contents

- [Database Issues](#database-issues)
- [Redis Issues](#redis-issues)
- [Docker Issues](#docker-issues)
- [API Errors](#api-errors)
- [Analysis Engine Issues](#analysis-engine-issues)
- [Frontend Issues](#frontend-issues)
- [CI/CD Issues](#cicd-issues)
- [Debug Checklist](#debug-checklist)

---

## Database Issues

### PostgreSQL won't start

**Symptoms:** `blockscope_db` container exits immediately, backend can't connect.

**Solutions:**
```bash
# Check container logs
docker logs blockscope_db

# Port 5432 already in use (local PostgreSQL running)
sudo lsof -i :5432            # Find what's using the port
sudo systemctl stop postgresql # Stop local PostgreSQL

# Or change the host port in docker-compose.yml:
# ports: "5433:5432"
```

### "DATABASE_URL environment variable is required"

**Cause:** Missing or malformed `DATABASE_URL` in env file.

**Solution:**
```bash
# Ensure backend/.env.development exists and contains:
DATABASE_URL=postgresql://blockscope_dev:dev_password_123@db:5432/blockscope_dev

# For non-Docker local dev, use localhost instead of 'db':
DATABASE_URL=postgresql://blockscope_dev:dev_password_123@localhost:5432/blockscope_dev
```

### Connection pool exhaustion

**Symptoms:** `TimeoutError: QueuePool limit overflow`, slow API responses.

**Solutions:**
```bash
# Increase pool settings in .env:
DB_POOL_SIZE=30          # Default: 20
DB_MAX_OVERFLOW=15       # Default: 10
DB_POOL_TIMEOUT=60       # Default: 30

# Check active connections
docker exec blockscope_db psql -U blockscope_dev -c "SELECT count(*) FROM pg_stat_activity;"
```

### Migration errors

**Symptoms:** `alembic upgrade head` fails, table conflicts.

**Solutions:**
```bash
# View current migration state
cd backend
alembic current

# Force stamp to a specific revision (use with caution)
alembic stamp head

# Generate a new migration from current models
alembic revision --autogenerate -m "fix schema"

# Reset everything (development only!)
docker compose down -v  # Destroys volumes
docker compose up -d
```

---

## Redis Issues

### Redis connection timeout

**Symptoms:** Rate limiting not working, `ConnectionError: Error connecting to Redis`.

**Solutions:**
```bash
# Check Redis container is running
docker ps | grep redis

# Test Redis connectivity
docker exec blockscope_redis redis-cli ping
# Expected: PONG

# Check Redis URL in .env:
REDIS_URL=redis://redis:6379/0  # Docker
REDIS_URL=redis://localhost:6379/0  # Local dev
```

### Redis authentication failure

**Symptoms:** `NOAUTH Authentication required` in production.

**Solution:**
```bash
# In production, Redis requires a password. Ensure both match:
# docker-compose.prod.yml:
#   command: redis-server --requirepass ${REDIS_PASSWORD}

# backend/.env:
REDIS_URL=redis://:your_password@redis:6379/0
```

### Rate limiting not working

**Symptoms:** No `429 Too Many Requests` responses, no rate limit headers.

**Check:**
```bash
# 1. Is rate limiting enabled?
RATE_LIMIT_ENABLED=True  # in .env

# 2. Is Redis connected? Check /health endpoint:
curl http://localhost:8000/health
# Should show: "redis": "connected"

# 3. Check application logs
docker logs blockscope_backend | grep -i "rate"
```

---

## Docker Issues

### Port conflicts

**Symptoms:** `Bind for 0.0.0.0:5432 failed: port is already allocated`.

**Solution:**
```bash
# Find what's using the port
# Linux/Mac:
sudo lsof -i :5432
# Windows:
netstat -aon | findstr :5432

# Change the host-side port in docker-compose.yml:
ports:
  - "5433:5432"  # Use 5433 on host instead
```

### Container build failures

**Symptoms:** `npm ci` or `pip install` fails during build.

**Solutions:**
```bash
# Clean Docker build cache
docker builder prune -f

# Rebuild without cache
docker compose build --no-cache

# If npm install fails, try:
docker compose build --build-arg NPM_FLAGS="--legacy-peer-deps"
```

### Volume permission errors

**Symptoms:** `Permission denied` inside container, especially in production.

**Solution:**
```bash
# The production Dockerfile creates a non-root user.
# Ensure the upload and logs directories are writable:
docker exec blockscope-backend ls -la /app/logs /app/uploads

# Fix permissions:
docker exec -u root blockscope-backend chown -R appuser:appuser /app/logs /app/uploads
```

### Containers keep restarting

**Symptoms:** Container status shows `Restarting`, health check fails.

**Diagnosis:**
```bash
# Check why it's restarting
docker logs --tail 50 blockscope_backend

# Common causes:
# - Missing environment variables → check .env file
# - Database not ready → check depends_on and healthcheck
# - Port already in use → see "Port conflicts" above
```

---

## API Errors

### 401 Unauthorized

**Cause:** API key required but missing or invalid.

**Solutions:**
```bash
# Include the API key header:
curl -H "X-API-Key: bsc_your_key_here" http://localhost:8000/api/v1/scans/1

# Verify your key is valid:
# - Not expired
# - Not revoked
# - Correct prefix (bsc_)
```

### 429 Too Many Requests

**Cause:** Rate limit exceeded.

**Solutions:**
```bash
# Check rate limit headers in the response:
# X-RateLimit-Limit: 20
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1709571234

# Wait for the reset time, or authenticate with API key for higher limits

# For development, disable rate limiting:
RATE_LIMIT_ENABLED=False  # in .env
```

### 400 Bad Request — "Source code too short"

**Cause:** Source code is less than 10 characters.

**Solution:** Ensure you're sending actual Solidity source code, not a file path.

### 422 Validation Error

**Cause:** Request body doesn't match expected schema.

**Check:**
```bash
# Ensure proper Content-Type:
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"source_code": "pragma solidity ^0.8.0; contract Test {}"}'

# For file upload, use multipart/form-data:
curl -X POST http://localhost:8000/api/v1/scan/file \
  -F "file=@contract.sol"
```

### 500 Internal Server Error

**Diagnosis:**
```bash
# Check backend logs for the stack trace:
docker logs --tail 100 blockscope_backend

# Common causes:
# - Database connection lost
# - Slither binary not found
# - Malformed contract source (Slither crash)
```

---

## Analysis Engine Issues

### "Slither not available"

**Cause:** Slither binary not installed in the container.

**Solution:**
```bash
# Install Slither in the backend container
docker exec blockscope_backend pip install slither-analyzer

# Or add to requirements.txt and rebuild:
echo "slither-analyzer" >> backend/requirements.txt
docker compose build backend
docker compose up -d
```

### Slither analysis timeout

**Symptoms:** Scan takes too long and fails.

**Solution:**
```bash
# Increase timeout in .env:
SLITHER_TIMEOUT=600  # 10 minutes (default: 300)

# For very large contracts, consider breaking them into smaller files
```

### Solidity compiler version mismatch

**Symptoms:** Slither errors about `pragma solidity` version.

**Solution:**
```bash
# Install the matching solc version:
pip install solc-select
solc-select install 0.8.20
solc-select use 0.8.20

# Or update in .env:
SOLC_VERSION=0.8.20
```

### Empty scan results (no findings)

**Possible causes:**
1. **No custom rules registered** — the orchestrator starts with `rules=[]`
2. **Slither not installed** — analysis silently falls back to no findings
3. **Simple contracts** — may genuinely have no vulnerabilities

**Check:**
```bash
# The API response includes vulnerability count:
# "vulnerabilities_count": 0
# "overall_score": 100
# This is normal for clean contracts

# To verify Slither is working:
docker exec blockscope_backend python -c "from slither import Slither; print('OK')"
```

---

## Frontend Issues

### `npm install` fails

**Solutions:**
```bash
# Clear npm cache and retry
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps

# If still failing, check Node version:
node --version  # Should be 20+
```

### Vite dev server not accessible

**Symptoms:** `localhost:5173` not loading in browser.

**Solutions:**
```bash
# If running in Docker, ensure the port is exposed:
# docker-compose.yml should have:
# ports: "5173:5173"

# If running locally, check Vite is binding to all interfaces:
npm run dev -- --host 0.0.0.0
```

### CORS errors in browser console

**Symptoms:** `Access to fetch has been blocked by CORS policy`.

**Solutions:**
```bash
# 1. Check CORS_ORIGINS in backend .env includes your frontend URL:
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 2. If using a different port, add it:
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:5174

# 3. For development, security can be disabled:
# The app falls back to allow_origins=["*"] when security modules aren't loaded
```

### Build failures (`npm run build`)

**Solutions:**
```bash
# Check for TypeScript/ESLint errors:
cd frontend
npm run lint

# Build with verbose output:
npm run build -- --debug

# Common fix: install missing peer dependencies
npm install --legacy-peer-deps
```

---

## CI/CD Issues

### Backend tests failing in CI

**Common causes:**
1. **Database not ready**: CI uses service containers; check PostgreSQL health check
2. **Missing env vars**: Ensure all required vars are set in the workflow

**CI environment variables** (set in `backend-ci.yml`):
```yaml
env:
  DATABASE_URL: postgresql://test_user:test_password@localhost:5432/blockscope_test
  REDIS_URL: redis://localhost:6379/0
  SECRET_KEY: test-secret-key-for-ci-only-not-production
  JWT_SECRET_KEY: test-jwt-secret-key-for-ci-only-not-production
  ENVIRONMENT: testing
  TESTING: "True"
```

### Docker build fails in CI

**Solutions:**
```bash
# 1. Check if context path is correct in workflow
# file: docker/Dockerfile.backend.prod  (relative to repo root)

# 2. Clear GitHub Actions cache
# Go to Actions → Caches → Delete

# 3. Check GHCR login
# The GITHUB_TOKEN secret is auto-provided but needs packages:write permission
```

### Codecov upload fails

**Symptoms:** Coverage badge shows unknown, upload step fails.

**Solution:**
```bash
# Ensure CODECOV_TOKEN secret is set in GitHub repository settings
# Settings → Secrets and variables → Actions → New repository secret
```

---

## Debug Checklist

When something isn't working, run through this checklist:

### 1. Container Status
```bash
docker compose ps                    # All containers running?
docker compose logs --tail 20        # Any error messages?
```

### 2. Health Check
```bash
curl http://localhost:8000/health     # Backend healthy?
curl http://localhost:5173            # Frontend loading?
```

### 3. Configuration
```bash
# Debug endpoint (development only):
curl http://localhost:8000/debug/config

# Check environment:
docker exec blockscope_backend env | grep -E "DATABASE|REDIS|SECRET"
```

### 4. Database
```bash
# Can the backend reach PostgreSQL?
docker exec blockscope_backend python -c "
from app.core.database import test_connection
print('DB OK' if test_connection() else 'DB FAIL')
"
```

### 5. Logs
```bash
# Application logs
docker logs blockscope_backend --tail 50

# Log file (if enabled)
docker exec blockscope_backend cat /var/log/blockscope/app.log | tail -20
```

### 6. API Test
```bash
# Quick smoke test
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"source_code": "pragma solidity ^0.8.0; contract Test { function foo() public {} }"}'
```
