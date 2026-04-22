import shutil
import time
from pathlib import Path

try:
    import psutil as _psutil
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False

try:
    import redis as _redis_module
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _redis_module = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.database import engine
from app.core.settings import settings

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
    if not _REDIS_AVAILABLE:
        return {"status": "unavailable", "detail": "redis package not installed"}
    try:
        r = _redis_module.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_disk():
    # Use Path(__file__).anchor so the check targets the correct drive root
    # on Windows (e.g. "C:\\") and non-root Linux deployments, rather than
    # hard-coding "/" which can give misleading results on multi-drive setups.
    disk_root = Path(__file__).anchor
    usage = shutil.disk_usage(disk_root)
    percent_used = round((usage.used / usage.total) * 100, 1)
    free_gb = round(usage.free / (1024 ** 3), 2)
    status = "ok" if percent_used < 85 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "free_gb": free_gb, "path": disk_root}


def check_memory():
    if not _PSUTIL_AVAILABLE:
        return {"status": "unavailable", "detail": "psutil package not installed"}
    mem = _psutil.virtual_memory()
    percent_used = mem.percent
    available_mb = round(mem.available / (1024 ** 2), 1)
    status = "ok" if percent_used < 80 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "available_mb": available_mb}


def check_response_time():
    """Measure interpreter responsiveness with a lightweight in-process operation.

    Note: this intentionally benchmarks Python interpreter speed (sum of a
    small range) rather than making an outbound HTTP call, to avoid circular
    dependencies and network noise in the health check.  It is a proxy for
    "is the process severely CPU-starved" rather than end-to-end API latency.
    For true latency measurement use the /api/v1/performance endpoint.
    """
    start = time.time()

    # Lightweight CPU-bound work (no external calls, no I/O).
    _ = sum(range(1000))

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
        or r["status"] == "error"
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