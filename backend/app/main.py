"""
BlockScope API — Main Application Entry Point.

Configures FastAPI with:
- Request-ID middleware (X-Request-ID header propagation)
- Performance logging middleware
- CORS + security middleware
- Rate limiting (when Redis is available)
- Global exception handlers
- Health, root, and info endpoints
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Ensure the parent directory is importable
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logger import logger, set_request_id

try:
    from app.core.auth import APIKey, get_optional_api_key
except ImportError:  # pragma: no cover
    APIKey = type(None)  # type: ignore[assignment,misc]

    def get_optional_api_key() -> None:  # type: ignore[misc]
        return None

# ----------------------------------------------
# Settings (with graceful fallback)
# ----------------------------------------------
try:
    from app.core.config import print_config_summary, settings

    SECURITY_ENABLED: bool = True
except ImportError:

    class _FallbackSettings:  # type: ignore[no-redef]
        """Minimal stand-in settings used when the full config is unavailable."""

        APP_NAME: str = "BlockScope API"
        APP_VERSION: str = "0.1.0"
        DEBUG: bool = True
        ENABLE_API_DOCS: bool = True
        CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
        RATE_LIMIT_ENABLED: bool = False
        LOG_REQUESTS: bool = True
        ENVIRONMENT: str = "development"

    settings = _FallbackSettings()  # type: ignore[assignment]
    SECURITY_ENABLED = False
    logger.warning("Running without security modules — set up config to enable full security")

# ----------------------------------------------
# Routers
# ----------------------------------------------
try:
    from app.routers.scan import router as scan_router

    _scan_router_available: bool = True
except ImportError:
    logger.error("Scan router import failed — /api/v1/scan will not be available")
    scan_router = None  # type: ignore[assignment]
    _scan_router_available = False


# ----------------------------------------------
# Middleware definitions
# ----------------------------------------------

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

        status = response.status_code
        if elapsed_ms >= self.SLOW_REQUEST_THRESHOLD_MS:  # pragma: no cover
            logger.warning(
                "Slow request %s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra=log_extra,
            )
        elif status >= 500:
            logger.error(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra=log_extra,
            )
        elif status >= 400:
            logger.warning(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra=log_extra,
            )
        else:
            logger.debug(
                "%s %s → %d  (%.1f ms)",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra=log_extra,
            )

        return response


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
)

# ----------------------------------------------
# Middleware stack  (order matters — added last runs first)
# ----------------------------------------------

# 0. GZip compression — smallest-first: responses >= configured threshold are compressed
app.add_middleware(
    GZipMiddleware,
    minimum_size=getattr(settings, "GZIP_MINIMUM_SIZE", 1024),
)

# 1. Request ID — must be first so all subsequent middleware can read the ID
app.add_middleware(RequestIDMiddleware)

# 2. Performance logger
app.add_middleware(PerformanceLoggingMiddleware)

# 3. CORS / security
if SECURITY_ENABLED:
    try:
        from app.core.security import setup_security_middleware

        setup_security_middleware(app)
        logger.info("Security middleware enabled")
    except ImportError:
        logger.warning("Security middleware not available — falling back to basic CORS")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
else:
    app.add_middleware(  # pragma: no cover
        CORSMiddleware,
        allow_origins=["*"],   # Development only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.warning("Permissive CORS active — not suitable for production")  # pragma: no cover


# ----------------------------------------------
# Lifecycle events
# ----------------------------------------------

@app.on_event("startup")
async def startup_event() -> None:
    """Initialise external connections and log startup summary."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    if settings.DEBUG and SECURITY_ENABLED:  # pragma: no cover
        try:
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
            logger.warning("Redis connection failed — rate limiting disabled: %s", exc)

    # Database connectivity
    try:
        from app.core.database import engine, text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.warning("Database connection failed on startup: %s", exc)

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Disconnect from external services on graceful shutdown."""
    logger.info("Shutting down %s …", settings.APP_NAME)

    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:  # pragma: no cover
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.disconnect()
            logger.info("Redis disconnected")
        except Exception:
            pass

    logger.info("Application shutdown complete")


# ----------------------------------------------
# Global exception handlers
# ----------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a structured 404 response."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "The requested resource was not found.",
            "path": str(request.url.path),
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a structured 500 response without leaking internal details."""
    request_id = getattr(request.state, "request_id", "")
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )


# ----------------------------------------------
# System endpoints
# ----------------------------------------------

@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> Dict[str, Any]:
    """
    Return application health status.

    Checks database and (optionally) Redis connectivity.
    Status is ``"healthy"`` when all checks pass, ``"degraded"`` otherwise.

    Returns:
        Dict with ``status``, ``version``, and component connectivity flags.
    """
    health: Dict[str, Any] = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
    }

    # Database
    try:
        from app.core.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception:
        health["database"] = "disconnected"
        health["status"] = "degraded"

    # Redis
    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:  # pragma: no cover
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.redis.ping()
            health["redis"] = "connected"
        except Exception:
            health["redis"] = "disconnected"

    return health


@app.get("/", tags=["System"], summary="API root")
async def root() -> Dict[str, Any]:
    """
    Return API overview information.

    Returns:
        Dict with app name, version, and key endpoint paths.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "description": "Smart Contract Vulnerability Scanner",
        "docs": "/docs" if settings.ENABLE_API_DOCS else None,
        "health": "/health",
        "endpoints": {"scan": "/api/v1/scan"},
        "security": {
            "enabled": SECURITY_ENABLED,
            "rate_limiting": settings.RATE_LIMIT_ENABLED if SECURITY_ENABLED else False,
            "authentication": "API Key (optional)" if SECURITY_ENABLED else "None",
        },
    }


@app.get("/api/v1/info", tags=["System"], summary="Detailed API info")
async def api_info() -> Dict[str, Any]:
    """
    Return detailed API and configuration information.

    Returns:
        Dict with environment, security configuration, and upload limits.
    """
    info: Dict[str, Any] = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "debug": settings.DEBUG,
    }

    if SECURITY_ENABLED:
        info["security"] = {
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "cors_configured": True,
            "api_key_authentication": True,
        }
        info["limits"] = {
            "max_upload_size": (
                f"{getattr(settings, 'MAX_UPLOAD_SIZE', 5_242_880) / 1024 / 1024:.1f} MB"
            ),
            "allowed_extensions": getattr(settings, "ALLOWED_EXTENSIONS", [".sol"]),
        }

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
    metrics: Dict[str, Any] = {}

    # Analysis result cache
    try:
        from analysis.cache import analysis_cache
        metrics["analysis_cache"] = analysis_cache.stats
    except Exception:
        metrics["analysis_cache"] = "unavailable"

    # Slither parse cache
    try:
        from analysis.slither_wrapper import SlitherWrapper
        metrics["slither_parse_cache_size"] = SlitherWrapper.parse_cache_size()
    except Exception:
        metrics["slither_parse_cache_size"] = "unavailable"

    # DB pool
    try:
        from app.core.database import engine
        pool = engine.pool
        metrics["db_pool"] = {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
        }
    except Exception:
        metrics["db_pool"] = "unavailable"

    return metrics


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
    async def debug_routes() -> Dict[str, Any]:
        """List all registered routes (debug only)."""
        return {
            "routes": [
                {"path": r.path, "methods": sorted(r.methods), "name": r.name}
                for r in app.routes
                if hasattr(r, "methods")
            ]
        }

    @app.get("/debug/config", tags=["Debug"], include_in_schema=False)
    async def debug_config() -> Dict[str, Any]:
        """Show sanitised configuration (debug only)."""
        if SECURITY_ENABLED:
            return {
                "security_enabled": True,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
                "rate_limiting": settings.RATE_LIMIT_ENABLED,
                "cors_origins": settings.CORS_ORIGINS[:3],
            }
        return {
            "security_enabled": False,
            "message": "Running in basic mode — configure environment variables to enable security.",
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
