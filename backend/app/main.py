"""
BlockScope API - Main Application
Secure, production-ready FastAPI application with comprehensive security features
"""

import logging
import sys
from pathlib import Path
import time
from fastapi import Request

from prometheus_client import generate_latest
from fastapi.responses import Response
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS, CACHE_HITS, CACHE_MISSES, ACTIVE_USERS, APP_UPTIME,START_TIME
from app.routers.health import router as health_router
from app.routers.health import startup_complete
from fastapi import FastAPI, Request
from app.core.logging_config import setup_logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Try to import security modules, fall back gracefully if not available
try:
    from app.core.settings import settings

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

# Import routers
try:
    from app.routers.scan import router as scan_router
except ImportError:
    print("⚠️  Scan router not found. Please ensure app/routers/scan.py exists.")
    scan_router = None

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
# ===================================
# CREATE FASTAPI APP
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    ACTIVE_REQUESTS.inc()

    start = time.time()

    logger.info(f"→ {request.method} {request.url.path}")

    # Track authenticated users via API key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        ACTIVE_USERS.inc()

    response = await call_next(request)

    duration = round((time.time() - start) * 1000, 2)

    # logging
    logger.info(
        f"← {request.method} {request.url.path} "
        f"| status={response.status_code} | {duration}ms"
    )

    # metrics
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

# ===================================
# STARTUP EVENTS
# ===================================
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    import app.routers.health as health
    health.startup_complete = True
    logger.info("BlockScope API starting up")

    # Initialize logging configuration
    try:
        logger.info("Logging configured with rotation")
    except ImportError:
        logger.warning("Logging configuration module not available")
    except Exception as exc:
        logger.warning("Logging configuration failed: %s", exc)

    # Connect to Redis if security enabled
    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.connect()
            logger.info("✅ Redis connected for rate limiting")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")

    # Test database connection
    try:
        from app.core.database import engine

        with engine.connect() as conn:
            logger.info("✅ Database connected")
    except Exception as e:
        logger.warning(f"⚠️  Database connection failed: {e}")

    logger.info("✅ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down application")

    # Disconnect Redis if connected
    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.disconnect()
            logger.info("✅ Redis disconnected")
        except Exception:
            pass

    logger.info("✅ Application shutdown complete")


# ===================================
# MIDDLEWARE CONFIGURATION
# ===================================

# Add security middleware if available
if SECURITY_ENABLED:
    try:
        from app.core.security import setup_security_middleware

        setup_security_middleware(app)
        logger.info("✅ Security middleware enabled")
    except ImportError:
        logger.warning("⚠️  Security middleware not available")

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
    logger.warning("⚠️  Running with permissive CORS (development mode)")

# Add rate limiting middleware if available
if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:
    try:
        from app.core.rate_limit import RateLimitMiddleware, rate_limit_redis

        @app.on_event("startup")
        async def add_rate_limit():
            app.add_middleware(
                RateLimitMiddleware, redis_client=rate_limit_redis.redis, enabled=True
            )

        logger.info("✅ Rate limiting enabled")
    except ImportError:
        logger.warning("⚠️  Rate limiting not available")

# ===================================
# EXCEPTION HANDLERS
# ===================================


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "The requested resource was not found",
            "path": str(request.url),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred. Please try again later.",
        },
    )


# ===================================
# HEALTH & INFO ENDPOINTS
# ===================================


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Health status and version info
    """
    health_status = {"status": "healthy", "version": settings.APP_VERSION, "app": settings.APP_NAME}

    # Check database
    try:
        from app.core.database import engine

        with engine.connect():
            health_status["database"] = "connected"
    except Exception:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Redis
    if SECURITY_ENABLED and settings.RATE_LIMIT_ENABLED:
        try:
            from app.core.rate_limit import rate_limit_redis

            await rate_limit_redis.redis.ping()
            health_status["redis"] = "connected"
        except:
            health_status["redis"] = "disconnected"

    return health_status


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


# ===================================
# INCLUDE ROUTERS
# ===================================

# Include scan router
if scan_router:
    app.include_router(scan_router, prefix="/api/v1", tags=["Scanning"])
    logger.info("✅ Scan router registered at /api/v1/scan")
else:
    logger.error("❌ Scan router not available")

# ===================================
# DEVELOPMENT HELPERS
# ===================================

if settings.DEBUG:

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


# ===================================
# MAIN ENTRY POINT
# ===================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=getattr(settings, "HOST", "0.0.0.0"),
        port=getattr(settings, "PORT", 8000),
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
