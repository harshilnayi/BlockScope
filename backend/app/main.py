"""
BlockScope API - Main Application
Secure, production-ready FastAPI application with comprehensive security features
"""

import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging_config import setup_logging
from app.core.logger import get_request_id, log_error_context, logger, set_request_id
from app.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    CACHE_HITS,
    CACHE_MISSES,
    ACTIVE_USERS,
    APP_UPTIME,
    START_TIME,
)
from app.routers.health import router as health_router

try:
    from app.core.auth import APIKey, get_optional_api_key
except ImportError:  # pragma: no cover
    APIKey = type(None)  # type: ignore[assignment,misc]

    def get_optional_api_key() -> None:  # type: ignore[misc]
        return None

# Setup logging
setup_logging()

# ----------------------------------------------
# Settings (with graceful fallback)
# ----------------------------------------------
try:
    from app.core.settings import settings

    SECURITY_ENABLED = True
except ImportError:
    try:
        from app.core.config import settings  # type: ignore[no-redef]

        SECURITY_ENABLED = True
    except ImportError:
        # Fallback settings if core.config not available yet
        class Settings:
            APP_NAME = "BlockScope API"
            APP_VERSION = "0.1.0"
            DEBUG = True
            ENABLE_API_DOCS = True
            CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
            RATE_LIMIT_ENABLED = False
            LOG_REQUESTS = True

        settings = Settings()
        SECURITY_ENABLED = False
        print("⚠️  Running without security modules. Run setup to enable full security.")

# ----------------------------------------------
# Routers
# ----------------------------------------------
try:
    from app.routers.scan import router as scan_router
    _scan_router_available = True
except ImportError:
    print("Scan router not found. Please ensure app/routers/scan.py exists.")
    scan_router = None
    _scan_router_available = False

# ----------------------------------------------
# Middleware definitions
# ----------------------------------------------

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request ID to every incoming request.

    The ID is sourced from the ``X-Request-ID`` header when provided
    by the caller (e.g. a load-balancer or API gateway); otherwise a
    UUID4 is generated.  The ID is stored in:

    - ``request.state.request_id`` — for use in endpoint code.
    - The ``app.core.logger`` context var — for automatic log correlation.
    - The ``X-Request-ID`` response header — so callers can correlate.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process a request, injecting and propagating the request ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware / endpoint in the chain.

        Returns:
            HTTP response with ``X-Request-ID`` header attached.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log each request's method, path, status code, and wall-clock duration.

    Records are emitted at DEBUG for 2xx/3xx, WARNING for 4xx, and ERROR
    for 5xx responses.  Slow requests (>= 1 s) are also flagged at WARNING
    regardless of status code.
    """

    SLOW_REQUEST_THRESHOLD_MS: float = 1_000.0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Time the request and log a summary after completion.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware / endpoint in the chain.

        Returns:
            Unchanged HTTP response.
        """
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        request_id: str = getattr(request.state, "request_id", "")
        log_extra: Dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": elapsed_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }

        status_code = response.status_code
        if elapsed_ms >= self.SLOW_REQUEST_THRESHOLD_MS:  # pragma: no cover
            logger.warning(
                "Slow request %s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra=log_extra,
            )
        elif status_code >= 500:
            logger.error(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra=log_extra,
            )
        elif status_code >= 400:
            logger.warning(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra=log_extra,
            )
        else:
            logger.debug(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra=log_extra,
            )

        return response


# ----------------------------------------------
# Lifecycle (startup + shutdown)
# ----------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and graceful shutdown via lifespan context."""
    # -- Startup ----------------------------------------------------------
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    import app.routers.health as health

    health.startup_complete = True

    if settings.DEBUG and SECURITY_ENABLED:  # pragma: no cover
        try:
            from app.core.settings import print_config_summary  # type: ignore[attr-defined]
            print_config_summary()
        except Exception:
            pass

    # Redis (rate limiting)
    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:  # pragma: no cover
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.connect()
            logger.info("Redis connected for rate limiting")
        except Exception as exc:
            logger.warning("Redis connection failed - rate limiting disabled: %s", exc)

    # Database connectivity
    try:
        from app.core.database import engine, text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.warning("Database connection failed on startup: %s", exc)

    logger.info("Application startup complete")

    yield  # <- application runs here

    # -- Shutdown ---------------------------------------------------------
    logger.info("Shutting down %s ...", settings.APP_NAME)

    # Shut down the shared analysis thread pool cleanly so worker threads
    # are not left dangling when uvicorn exits.
    try:
        from analysis.orchestrator import _ANALYSIS_POOL
        _ANALYSIS_POOL.shutdown(wait=False, cancel_futures=True)
        logger.info("Analysis thread pool shut down")
    except Exception as exc:  # pragma: no cover
        logger.debug("Thread pool shutdown skipped: %s", exc)

    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:  # pragma: no cover
        try:
            from app.core.rate_limit import rate_limit_redis
            await rate_limit_redis.disconnect()
            logger.info("Redis disconnected")
        except Exception:
            pass

    logger.info("Application shutdown complete")


# ----------------------------------------------
# FastAPI application instance
# ----------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "BlockScope — Smart Contract Vulnerability Scanner. "
        "Detects reentrancy, integer overflows, access control issues and more."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    lifespan=lifespan,
)

app.include_router(health_router)

# ----------------------------------------------
# Middleware stack  (order matters — added last runs first)
# ----------------------------------------------

# 0. GZip compression — smallest-first: responses >= configured threshold are compressed
app.add_middleware(
    GZipMiddleware,
    minimum_size=getattr(settings, "GZIP_MINIMUM_SIZE", 1024),
)

# 1. Request ID + performance logging
app.add_middleware(RequestIDMiddleware)
app.add_middleware(PerformanceLoggingMiddleware)

# Add security middleware if available
if SECURITY_ENABLED:
    try:
        from app.core.security import setup_security_middleware

        setup_security_middleware(app)
        logger.info("Security middleware enabled")
    except ImportError:
        logger.warning("Security middleware not available")

        # Fallback basic CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
else:
    # Basic CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # ⚠️ Development only!
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.warning("Running with permissive CORS (development mode)")

# Add rate limiting middleware if available
if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:
    try:
        from app.core.rate_limit import RateLimitMiddleware

        app.add_middleware(RateLimitMiddleware, enabled=True)

        logger.info("Rate limiting enabled")
    except ImportError:
        logger.warning("Rate limiting not available")

# ----------------------------------------------
# Prometheus metrics endpoint
# ----------------------------------------------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    ACTIVE_REQUESTS.inc()

    start = time.time()

    logger.info("→ %s %s", request.method, request.url.path)

    # Track authenticated users via API key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        ACTIVE_USERS.inc()

    response = await call_next(request)

    duration = round((time.time() - start) * 1000, 2)

    logger.info(
        "← %s %s | status=%s | %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        endpoint=request.url.path
    ).observe(duration / 1000)

    APP_UPTIME.set(time.time() - START_TIME)

    ACTIVE_REQUESTS.dec()

    if api_key:
        ACTIVE_USERS.dec()

    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# ----------------------------------------------
# Global exception handlers
# ----------------------------------------------


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "The requested resource was not found",
            "path": str(request.url),
            "request_id": getattr(request.state, "request_id", get_request_id()),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    log_error_context(
        logger,
        "Internal server error",
        exc,
        context={"request_id": getattr(request.state, "request_id", get_request_id())},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred. Please try again later.",
            "request_id": getattr(request.state, "request_id", get_request_id()),
        },
    )

# ----------------------------------------------
# System endpoints
# ----------------------------------------------


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API info and available endpoints
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "description": "Smart Contract Vulnerability Scanner",
        "docs": "/docs" if settings.ENABLE_API_DOCS else None,
        "health": "/health",
        "endpoints": {
            "scan": "/api/v1/scan",
        },
        "security": {
            "enabled": SECURITY_ENABLED,
            "rate_limiting": settings.RATE_LIMIT_ENABLED if SECURITY_ENABLED else False,
            "authentication": "API Key (optional)" if SECURITY_ENABLED else "None",
        },
    }


@app.get("/api/v1/info", tags=["System"])
async def api_info():
    """
    Detailed API information.

    Returns:
        dict: Detailed API configuration
    """
    info = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "debug": settings.DEBUG,
    }

    if SECURITY_ENABLED:
        info.update(
            {
                "security": {
                    "rate_limiting": settings.RATE_LIMIT_ENABLED,
                    "cors_configured": True,
                    "api_key_authentication": True,
                },
                "limits": {
                    "max_upload_size": f"{getattr(settings, 'MAX_UPLOAD_SIZE', 5242880) / 1024 / 1024:.1f}MB",
                    "allowed_extensions": getattr(settings, "ALLOWED_EXTENSIONS", [".sol"]),
                },
            }
        )

    return info


@app.get("/api/v1/performance", tags=["System"], summary="Performance & cache metrics")
async def performance_metrics() -> Dict[str, Any]:
    """
    Return live performance and cache health metrics.

    Includes analysis cache hit-rate, Slither parse-cache size,
    and database connection pool status.

    Returns:
        Dict with cache and database pool metrics.
    """
    perf_metrics: Dict[str, Any] = {}

    # Analysis result cache
    try:
        from analysis.cache import analysis_cache
        perf_metrics["analysis_cache"] = analysis_cache.stats
    except Exception:
        perf_metrics["analysis_cache"] = "unavailable"

    # Slither parse cache
    try:
        from analysis.slither_wrapper import SlitherWrapper
        perf_metrics["slither_parse_cache_size"] = SlitherWrapper.parse_cache_size()
    except Exception:
        perf_metrics["slither_parse_cache_size"] = "unavailable"

    # DB pool
    try:
        from app.core.database import engine
        pool = engine.pool
        perf_metrics["db_pool"] = {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
        }
    except Exception:
        perf_metrics["db_pool"] = "unavailable"

    return perf_metrics


@app.post("/api/v1/cache/invalidate", tags=["System"], summary="Clear analysis cache")
async def invalidate_cache(
    request: Request,
    api_key: Optional[Any] = Depends(get_optional_api_key),
) -> Dict[str, Any]:
    """
    Evict all entries from the in-memory analysis result cache.

    Useful after deploying new analysis rules or Slither upgrades.
    In debug mode this endpoint is open for local development.
    In non-debug environments a valid API key is required.

    Returns:
        Dict with number of entries cleared.
    """
    if not settings.DEBUG and not api_key:
        if SECURITY_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid API key is required to invalidate caches.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cache invalidation is disabled outside debug mode.",
        )

    try:
        from analysis.cache import analysis_cache
        from analysis.slither_wrapper import SlitherWrapper

        cleared_analysis = analysis_cache.clear()
        cleared_slither = SlitherWrapper.clear_parse_cache()
        logger.info(
            "Cache invalidated via API",
            extra={
                "analysis_entries": cleared_analysis,
                "slither_entries": cleared_slither,
                "request_id": getattr(request.state, "request_id", ""),
            },
        )
        return {
            "analysis_cache_cleared": cleared_analysis,
            "slither_parse_cache_cleared": cleared_slither,
            "message": "All caches cleared successfully",
        }
    except Exception as exc:
        logger.error("Cache invalidation failed", exc_info=exc)
        return {"error": str(exc)}


# ----------------------------------------------
# Routers
# ----------------------------------------------
if _scan_router_available and scan_router is not None:
    app.include_router(scan_router, prefix="/api/v1", tags=["Scanning"])
    logger.info("Scan router mounted at /api/v1/scan")
else:  # pragma: no cover
    logger.error("Scan router unavailable — scanning endpoints not registered")

# ----------------------------------------------
# Debug-only endpoints
# ----------------------------------------------
if settings.DEBUG:  # pragma: no cover

    @app.get("/debug/routes", tags=["Debug"], include_in_schema=False)
    async def debug_routes():
        """List all available routes (debug only)"""
        routes = []
        for route in app.routes:
            if hasattr(route, "methods"):
                routes.append(
                    {"path": route.path, "methods": list(route.methods), "name": route.name}
                )
        return {"routes": routes}

    @app.get("/debug/config", tags=["Debug"], include_in_schema=False)
    async def debug_config():
        """Show current configuration (debug only)"""
        if SECURITY_ENABLED:
            return {
                "security_enabled": True,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
                "rate_limiting": settings.RATE_LIMIT_ENABLED,
                "cors_origins": settings.CORS_ORIGINS[:3],  # First 3 only
            }
        else:
            return {
                "security_enabled": False,
                "message": "Running in basic mode. Enable security features by setting up core modules.",
            }


# ----------------------------------------------
# Direct execution entry point
# ----------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "main:app",
        host=getattr(settings, "HOST", "0.0.0.0"),
        port=getattr(settings, "PORT", 8000),
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
