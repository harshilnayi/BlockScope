from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from backend.analysis import AnalysisOrchestrator, ScanRequest, ScanResult
from backend.app.core.database import get_db
from backend.app.models.scan import Scan
from backend.app.schemas.scan_schema import ScanRequest, ScanResponse


router = APIRouter(prefix="/api/v1", tags=["scans"])

# Initialize orchestrator once at module load
orchestrator = AnalysisOrchestrator(rules=[])


@router.post("/scan", response_model=ScanResponse)
def scan_contract(
    request: ScanRequest,
    db: Session = Depends(get_db)
):
    """
    Scan a Solidity contract for vulnerabilities.
    
    Takes source code and optional contract name, runs analysis,
    stores result in database, and returns structured findings.
    """
    try:
        # 1. Create ScanRequest from API input
        scan_request = ScanRequest(
            source_code=request.source_code,
            contract_name=request.contract_name or "UnnamedContract",
            file_path="api_upload"
        )
        
        # 2. Run analysis via orchestrator
        scan_result = orchestrator.analyze(scan_request)
        
        # 3. Convert findings to JSON-serializable format
        findings_json = [
            {
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "line_number": getattr(f, "line_number", None),
            }
            for f in scan_result.findings
        ]
        
        # 4. Create database record
        scan_record = Scan(
            contract_name=scan_result.contract_name,
            source_code=scan_result.source_code,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            scanned_at=datetime.utcnow()
        )
        
        # 5. Store in database
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)
        
        # 6. Return response with database ID
        return ScanResponse(
            contract_name=scan_result.contract_name,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            timestamp=scan_record.scanned_at,
            scan_id=scan_record.id
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/scans", response_model=list[ScanResponse])
def list_scans(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get list of all scans with pagination.
    
    Returns the most recent scans up to the specified limit.
    """
    try:
        scans = db.query(Scan).order_by(Scan.scanned_at.desc()).offset(skip).limit(limit).all()
        
        # Convert each scan to response format
        return [
            ScanResponse(
                contract_name=scan.contract_name,
                vulnerabilities_count=scan.vulnerabilities_count,
                severity_breakdown=scan.severity_breakdown,
                overall_score=scan.overall_score,
                summary=scan.summary,
                findings=scan.findings or [],
                timestamp=scan.scanned_at,
                scan_id=scan.id
            )
            for scan in scans
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scans: {str(e)}")


@router.get("/scans/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific scan by ID.
    
    Returns full scan details including findings and analysis results.
    """
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        
        if not scan:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        return ScanResponse(
            contract_name=scan.contract_name,
            vulnerabilities_count=scan.vulnerabilities_count,
            severity_breakdown=scan.severity_breakdown,
            overall_score=scan.overall_score,
            summary=scan.summary,
            findings=scan.findings or [],
            timestamp=scan.scanned_at,
            scan_id=scan.id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scan: {str(e)}")
