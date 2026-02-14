"""
BlockScope Scan Router - Security Upgraded
Maintains existing scan logic while adding security features
"""

from datetime import datetime
from typing import Optional

# Import existing modules (keep your structure)
from analysis import AnalysisOrchestrator
from analysis import ScanRequest as AnalysisScanRequest
from app.core.database import get_db
from app.models.scan import Scan
from app.schemas.scan_schema import ScanRequest, ScanResponse
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

# Import security modules (new - gracefully handle if not available)
try:
    from app.core.auth import APIKey, get_optional_api_key
    from app.core.rate_limit import rate_limit
    from app.core.security import FileValidator, InputSanitizer

    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False
    print("⚠️  Security modules not available. Running without enhanced security.")
    # Define dummy dependencies
    get_optional_api_key = lambda: None
    APIKey = type(None)
    rate_limit = lambda **kwargs: lambda func: func


router = APIRouter(tags=["scans"])

# Initialize orchestrator once at module load
orchestrator = AnalysisOrchestrator(rules=[])

# Initialize file validator if security enabled
if SECURITY_ENABLED:
    file_validator = FileValidator()
    input_sanitizer = InputSanitizer()


# Helper: conditional rate limiting decorator
def conditional_rate_limit(**kwargs):
    """Apply rate limiting only if security is enabled."""
    if SECURITY_ENABLED:
        return rate_limit(**kwargs)
    return lambda func: func


# Helper: conditional API key dependency
def _get_optional_api_key_dep():
    """Returns None when security is disabled."""
    return None


_api_key_dep = get_optional_api_key if SECURITY_ENABLED else _get_optional_api_key_dep


@router.post("/scan", response_model=ScanResponse)
@conditional_rate_limit(per_minute=5, per_hour=20)
async def scan_contract(
    request: ScanRequest,
    db: Session = Depends(get_db),
    api_key: Optional[APIKey] = Depends(_api_key_dep),
):
    """
    Scan a Solidity contract for vulnerabilities.

    Takes source code and optional contract name, runs analysis,
    stores result in database, and returns structured findings.

    **Security Features:**
    - Rate limiting: 5 requests/minute, 20 requests/hour (unauthenticated)
    - API key authentication: Optional, provides higher rate limits
    - Input validation: Source code sanitization
    - File size limits: Enforced via request validation
    """
    try:
        # Security: Sanitize inputs if security enabled
        if SECURITY_ENABLED:
            source_code = input_sanitizer.sanitize_string(
                request.source_code, max_length=500000  # 500KB max
            )
            contract_name = input_sanitizer.sanitize_filename(
                request.contract_name or "UnnamedContract"
            )
        else:
            source_code = request.source_code
            contract_name = request.contract_name or "UnnamedContract"

        # Validation: Check source code length
        if len(source_code) < 10:
            raise HTTPException(
                status_code=400, detail="Source code too short. Minimum 10 characters required."
            )

        if len(source_code) > 500000:  # 500KB
            raise HTTPException(
                status_code=400, detail="Source code too large. Maximum 500KB allowed."
            )

        # 1. Create ScanRequest from API input (your existing logic)
        scan_request = AnalysisScanRequest(
            source_code=source_code, contract_name=contract_name, file_path="api_upload"
        )

        # 2. Run analysis via orchestrator (your existing logic)
        scan_result = orchestrator.analyze(scan_request)

        # 3. Convert findings to JSON-serializable format (your existing logic)
        findings_json = [
            {
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "line_number": getattr(f, "line_number", None),
            }
            for f in scan_result.findings
        ]

        # 4. Create database record (your existing logic)
        scan_record = Scan(
            contract_name=scan_result.contract_name,
            source_code=scan_result.source_code,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            scanned_at=datetime.utcnow(),
        )

        # 5. Store in database (your existing logic)
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        # 6. Return response with database ID (your existing logic)
        return ScanResponse(
            contract_name=scan_result.contract_name,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            timestamp=scan_record.scanned_at,
            scan_id=scan_record.id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        # Security: Don't expose internal errors in production
        import logging

        logging.error(f"Scan analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please check your contract syntax and try again.",
        )


@router.post("/scan/file", response_model=ScanResponse)
@conditional_rate_limit(per_minute=5, per_hour=20)
async def scan_contract_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: Optional[APIKey] = Depends(_api_key_dep),
):
    """
    Scan a Solidity contract file for vulnerabilities.

    Accepts .sol file upload, validates the file, runs analysis,
    stores result in database, and returns structured findings.

    **Security Features:**
    - File validation: Size, extension, MIME type, content checks
    - Rate limiting: 5 uploads/minute, 20 uploads/hour
    - API key authentication: Optional, provides higher rate limits
    """
    try:
        # Security: Validate file if security enabled
        if SECURITY_ENABLED:
            is_valid, error = await file_validator.validate_file(file)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error)

        # Read file content
        source_code = await file.read()

        # Decode to string
        try:
            source_code = source_code.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

        # Extract contract name from filename
        contract_name = file.filename.replace(".sol", "") if file.filename else "UnnamedContract"

        # Security: Sanitize filename
        if SECURITY_ENABLED:
            contract_name = input_sanitizer.sanitize_filename(contract_name)

        # Create scan request
        scan_request = AnalysisScanRequest(
            source_code=source_code,
            contract_name=contract_name,
            file_path=file.filename or "uploaded_file.sol",
        )

        # Run analysis
        scan_result = orchestrator.analyze(scan_request)

        # Convert findings
        findings_json = [
            {
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "line_number": getattr(f, "line_number", None),
            }
            for f in scan_result.findings
        ]

        # Create database record
        scan_record = Scan(
            contract_name=scan_result.contract_name,
            source_code=scan_result.source_code,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            scanned_at=datetime.utcnow(),
        )

        # Store in database
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        # Return response
        return ScanResponse(
            contract_name=scan_result.contract_name,
            vulnerabilities_count=scan_result.vulnerabilities_count,
            severity_breakdown=scan_result.severity_breakdown,
            overall_score=scan_result.overall_score,
            summary=scan_result.summary,
            findings=findings_json,
            timestamp=scan_record.scanned_at,
            scan_id=scan_record.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"File scan error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="File analysis failed. Please check your file and try again."
        )


@router.get("/scans", response_model=list[ScanResponse])
async def list_scans(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    api_key: Optional[APIKey] = Depends(_api_key_dep),
):
    """
    Get list of all scans with pagination.

    Returns the most recent scans up to the specified limit.
    """
    try:
        # Validation: Limit maximum page size
        if limit > 100:
            raise HTTPException(status_code=400, detail="Limit cannot exceed 100 items per page")

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
                scan_id=scan.id,
            )
            for scan in scans
        ]
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"List scans error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scans")


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    api_key: Optional[APIKey] = Depends(_api_key_dep),
):
    """
    Get a specific scan by ID.

    Returns full scan details including findings and analysis results.
    """
    try:
        # Validation: Check ID is positive
        if scan_id < 1:
            raise HTTPException(status_code=400, detail="Invalid scan ID")

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
            scan_id=scan.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"Get scan error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scan")


# Optional: Delete scan endpoint (with API key required)
if SECURITY_ENABLED:

    @router.delete("/scans/{scan_id}")
    async def delete_scan(
        scan_id: int,
        db: Session = Depends(get_db),
        api_key: APIKey = Depends(get_optional_api_key),  # Require API key
    ):
        """
        Delete a scan by ID.

        **Requires API key authentication.**
        """
        try:
            if not api_key:
                raise HTTPException(
                    status_code=401, detail="API key required for delete operations"
                )

            scan = db.query(Scan).filter(Scan.id == scan_id).first()

            if not scan:
                raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

            db.delete(scan)
            db.commit()

            return {"message": f"Scan {scan_id} deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            import logging

            logging.error(f"Delete scan error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete scan")
