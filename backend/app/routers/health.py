from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.database import engine

router = APIRouter(prefix="/health", tags=["health"])

startup_complete = False


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        # WHY 503: load balancers and Kubernetes only look at the HTTP status code.
        # Returning 200 with "not_ready" in the body means they think we're fine.
        # 503 tells them "stop sending traffic here".
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )


@router.get("/startup")
def startup():
    if startup_complete:
        return {"status": "started"}
    return JSONResponse(
        status_code=503,
        content={"status": "starting"}
    )