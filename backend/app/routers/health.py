import shutil
import time

import psutil
import redis
from app.core.config import settings
from app.core.database import engine
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])

startup_complete = False


# ── CHECKS ────────────────────────────────────────────────────────────────────


def check_database():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_redis():
    if not settings.RATE_LIMIT_ENABLED and not settings.TESTING:
        return {"status": "disabled"}

    try:
        r = redis.from_url(
            settings.redis_url_str,
            password=settings.REDIS_PASSWORD or None,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_disk():
    usage = shutil.disk_usage("/")
    percent_used = round((usage.used / usage.total) * 100, 1)
    free_gb = round(usage.free / (1024**3), 2)
    status = "ok" if percent_used < 85 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "free_gb": free_gb}


def check_memory():
    mem = psutil.virtual_memory()
    percent_used = mem.percent
    available_mb = round(mem.available / (1024**2), 1)
    status = "ok" if percent_used < 80 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "available_mb": available_mb}


def check_response_time():
    """Measure internal API responsiveness with a lightweight operation."""
    start = time.time()

    # Lightweight CPU-bound work (no external calls)
    total = sum(range(1000))

    elapsed_ms = round((time.time() - start) * 1000, 2)

    if elapsed_ms < 500:
        status = "healthy"
    elif elapsed_ms <= 1000:
        status = "warning"
    else:
        status = "critical"

    return {"response_time_ms": elapsed_ms, "status": status}


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("")
def health():
    db = check_database()
    redis_status = check_redis()

    overall_status = "healthy"
    redis_required = settings.RATE_LIMIT_ENABLED and not settings.TESTING
    if db["status"] == "error" or (redis_required and redis_status["status"] != "ok"):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "database": db["status"],
        "redis": redis_status["status"],
    }


@router.get("/ready")
def readiness():
    db = check_database()
    r = check_redis()
    disk = check_disk()
    memory = check_memory()
    response_time = check_response_time()

    checks = {
        "database": db,
        "redis": r,
        "disk": disk,
        "memory": memory,
        "response_time": response_time,
    }

    critical = (
        db["status"] == "error"
        or (settings.RATE_LIMIT_ENABLED and not settings.TESTING and r["status"] != "ok")
        or disk["status"] == "critical"
        or memory["status"] == "critical"
        or response_time["status"] == "critical"
    )

    if critical:
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})

    return {"status": "ready", "checks": checks}


@router.get("/startup")
def startup():
    if startup_complete:
        return {"status": "started"}
    return JSONResponse(status_code=503, content={"status": "starting"})
