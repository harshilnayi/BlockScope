import shutil
import time

import psutil
import redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.database import engine
from app.core.settings import settings

router = APIRouter(prefix="/health", tags=["health"])

startup_complete = False


def check_database():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_redis():
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_disk():
    usage = shutil.disk_usage("/")
    percent_used = round((usage.used / usage.total) * 100, 1)
    free_gb = round(usage.free / (1024 ** 3), 2)
    status = "ok" if percent_used < 85 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "free_gb": free_gb}


def check_memory():
    mem = psutil.virtual_memory()
    percent_used = mem.percent
    available_mb = round(mem.available / (1024 ** 2), 1)
    status = "ok" if percent_used < 80 else "warning" if percent_used < 95 else "critical"
    return {"status": status, "percent_used": percent_used, "available_mb": available_mb}

def check_latency(start_time: float):
    """Measure how long the health check itself has taken so far."""
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    if elapsed_ms > 5000:
        status = "critical"
    elif elapsed_ms > 2000:
        status = "slow"
    else:
        status = "ok"
    return {"status": status, "response_time_ms": elapsed_ms}


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
def readiness():
    start = time.time()

    db      = check_database()
    r       = check_redis()
    disk    = check_disk()
    memory  = check_memory()
    latency = check_latency(start)

    checks = {
        "database": db,
        "redis": r,
        "disk": disk,
        "memory": memory,
        "latency": latency,
    }

    critical = (
        db["status"] == "error"
        or r["status"] == "error"
        or disk["status"] == "critical"
        or memory["status"] == "critical"
        or latency["status"] == "critical"
    )

    if critical:
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})

    return {"status": "ready", "checks": checks}


@router.get("/startup")
def startup():
    if startup_complete:
        return {"status": "started"}
    return JSONResponse(status_code=503, content={"status": "starting"})