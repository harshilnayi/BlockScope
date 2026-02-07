from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.logger import logger
from backend.analysis.orchestrator import AnalysisOrchestrator
from backend.analysis.models import ScanRequest as EngineScanRequest
from app.core.database import get_db
from app.models.scan import Scan

router = APIRouter(prefix="/api/v1", tags=["scans"])

orchestrator = AnalysisOrchestrator(rules=[])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/scan")
async def scan_contract(
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    try:
        # -------- Missing file --------
        if file is None:
            raise HTTPException(status_code=400, detail="file is required")

        # -------- File type --------
        if not file.filename.endswith(".sol"):
            raise HTTPException(status_code=400, detail="only .sol files allowed")

        content = await file.read()

        # -------- Empty --------
        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="empty file")

        # -------- Size --------
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="file too large")

        source_code = content.decode(errors="ignore")
        contract_name = file.filename.replace(".sol", "")

        # -------- Run analysis (CORRECT WAY) --------
        try:
            engine_request = EngineScanRequest(
                source_code=source_code,
                contract_name=contract_name,
                file_path="api_upload"
            )

            result = orchestrator.analyze(engine_request)

        except TimeoutError:
            raise HTTPException(status_code=500, detail="analysis timeout")

        # -------- Prepare response --------
        vulnerabilities = [
            {
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "line_number": getattr(f, "line_number", None)
            }
            for f in result.findings
        ]

        scan_record = Scan(
            contract_name=contract_name,
            source_code=source_code,
            vulnerabilities_count=len(vulnerabilities),
            severity_breakdown=result.severity_breakdown,
            overall_score=result.overall_score,
            summary=result.summary,
            findings=vulnerabilities,
            scanned_at=datetime.utcnow()
        )

        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        return {
            "contract_name": contract_name,
            "vulnerabilities": vulnerabilities,
            "severity_breakdown": result.severity_breakdown,
            "overall_score": result.overall_score,
            "summary": result.summary,
            "scan_timestamp": scan_record.scanned_at.isoformat(),
            "scan_id": scan_record.id
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Scan failed")
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/scans")
def list_scans(db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(Scan.scanned_at.desc()).all()

    return [
        {
            "contract_name": s.contract_name,
            "vulnerabilities": s.findings or [],
            "severity_breakdown": s.severity_breakdown,
            "overall_score": s.overall_score,
            "summary": s.summary,
            "scan_timestamp": s.scanned_at.isoformat(),
            "scan_id": s.id
        }
        for s in scans
    ]


@router.get("/scans/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="scan not found")

    return {
        "contract_name": scan.contract_name,
        "vulnerabilities": scan.findings or [],
        "severity_breakdown": scan.severity_breakdown,
        "overall_score": scan.overall_score,
        "summary": scan.summary,
        "scan_timestamp": scan.scanned_at.isoformat(),
        "scan_id": scan.id
    }
