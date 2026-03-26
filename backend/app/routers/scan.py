"""
BlockScope Scan Router.

Endpoints:
    POST /scan          — Scan contract source code submitted as JSON.
    POST /scan/file     — Scan a .sol file uploaded via multipart form.
    GET  /scans         — List recent scans with pagination.
    GET  /scans/{id}    — Retrieve a single scan by ID.
    DELETE /scans/{id}  — Delete a scan (requires API key when security is on).

Design notes:
    - Code duplication is eliminated via ``_build_scan_record`` and
      ``_scan_result_to_response`` helpers.
    - Every endpoint logs its request ID and wall-clock duration.
    - All public surface is fully type-annotated.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from analysis import AnalysisOrchestrator
from analysis import ScanRequest as AnalysisScanRequest
from analysis.models import ScanResult
from app.core.database import get_by_id, get_db, paginate
from app.core.logger import PerformanceTimer, log_error_context, logger
from app.models.scan import Scan
from app.schemas.scan_schema import ScanRequest, ScanResponse

# ----------------------------------------------
# Security modules (optional, graceful fallback)
# ----------------------------------------------
try:
    from app.core.auth import APIKey, get_optional_api_key
    from app.core.rate_limit import rate_limit
    from app.core.security import FileValidator, InputSanitizer  # pragma: no cover

    SECURITY_ENABLED: bool = True  # pragma: no cover
except ImportError:
    SECURITY_ENABLED = False
    logger.warning("Security modules not available — running without enhanced security")

    def get_optional_api_key() -> None:  # type: ignore[misc]
        return None

    APIKey = type(None)  # type: ignore[assignment,misc]

    def rate_limit(**kwargs: Any):  # type: ignore[misc]
        return lambda func: func

# ----------------------------------------------
# Module-level singletons
# ----------------------------------------------
_scan_logger = logging.getLogger("blockscope.scan")

router = APIRouter(tags=["scans"])

# Single orchestrator instance shared across all requests
orchestrator = AnalysisOrchestrator(rules=[])

if SECURITY_ENABLED:  # pragma: no cover
    _file_validator = FileValidator()
    _input_sanitizer = InputSanitizer()


# ----------------------------------------------
# Helper utilities
# ----------------------------------------------

def _conditional_rate_limit(**kwargs: Any):
    """
    Return a rate-limit decorator only when security is enabled.

    This prevents import errors when security modules are absent.
    """
    if SECURITY_ENABLED:  # pragma: no cover
        return rate_limit(**kwargs)
    return lambda func: func


def _api_key_dep():
    """Return the appropriate API-key dependency based on security mode."""
    return get_optional_api_key if SECURITY_ENABLED else (lambda: None)


def _sanitize_source(source_code: str, contract_name: str) -> tuple[str, str]:
    """
    Sanitize source code and contract name when security is enabled.

    Args:
        source_code: Raw Solidity source code from the request.
        contract_name: Raw contract name from the request.

    Returns:
        Tuple of (sanitized_source_code, sanitized_contract_name).
    """
    if SECURITY_ENABLED:  # pragma: no cover
        source_code = _input_sanitizer.sanitize_string(source_code, max_length=500_000)
        contract_name = _input_sanitizer.sanitize_filename(contract_name)
    return source_code, contract_name


def _validate_source_length(source_code: str) -> None:
    """
    Raise ``HTTPException(400)`` if source code is outside accepted bounds.

    Args:
        source_code: The Solidity source code string to validate.

    Raises:
        HTTPException: 400 if source_code is too short or too long.
    """
    if len(source_code) < 10:
        raise HTTPException(
            status_code=400,
            detail=(
                "Source code is too short (minimum 10 characters). "
                "Please provide a valid Solidity contract."
            ),
        )
    if len(source_code) > 500_000:
        raise HTTPException(
            status_code=400,
            detail=(
                "Source code exceeds the 500 KB limit. "
                "Please split large contracts into smaller files."
            ),
        )


def _findings_to_json(scan_result: ScanResult) -> List[Dict[str, Any]]:
    """
    Convert a :class:`ScanResult`'s findings list to JSON-serialisable dicts.

    Args:
        scan_result: Completed scan result from the orchestrator.

    Returns:
        List of finding dictionaries ready for JSON serialisation.
    """
    return [
        {
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "line_number": getattr(f, "line_number", None),
        }
        for f in scan_result.findings
    ]


def _build_scan_record(scan_result: ScanResult, findings_json: List[Dict[str, Any]]) -> Scan:
    """
    Construct an ORM ``Scan`` instance from a completed scan result.

    Args:
        scan_result: Orchestrator output.
        findings_json: Pre-serialised findings list.

    Returns:
        Unsaved ``Scan`` ORM instance (caller must ``db.add`` + ``db.commit``).
    """
    return Scan(
        contract_name=scan_result.contract_name,
        source_code=scan_result.source_code,
        vulnerabilities_count=scan_result.vulnerabilities_count,
        severity_breakdown=scan_result.severity_breakdown,
        overall_score=scan_result.overall_score,
        summary=scan_result.summary,
        findings=findings_json,
        scanned_at=datetime.now(timezone.utc),
    )


def _scan_record_to_response(scan: Scan) -> ScanResponse:
    """
    Convert an ORM ``Scan`` instance to a ``ScanResponse`` Pydantic model.

    Args:
        scan: A committed (ID-bearing) Scan ORM object.

    Returns:
        ``ScanResponse`` ready for the API caller.
    """
    return ScanResponse(
        scan_id=scan.id,
        contract_name=scan.contract_name,
        vulnerabilities_count=scan.vulnerabilities_count,
        severity_breakdown=scan.severity_breakdown,
        overall_score=scan.overall_score,
        summary=scan.summary,
        findings=scan.findings or [],
        timestamp=scan.scanned_at,
    )


async def _run_analysis_and_persist(
    source_code: str,
    contract_name: str,
    file_path: str,
    db: Session,
    request_id: str = "",
) -> ScanResponse:
    """
    Core pipeline: run analysis → persist to DB → return response.

    This helper is shared by both the JSON and file-upload endpoints.

    The heavy ``orchestrator.analyze()`` call is CPU/IO-bound (Slither
    invokes the Solidity compiler under the hood).  Running it directly
    inside an ``async`` endpoint would block FastAPI's event loop and
    serialise all concurrent requests.  We offload it to a thread-pool
    worker via :func:`asyncio.to_thread` so the event loop stays free
    to accept and dispatch other requests while analysis runs.

    Args:
        source_code: Solidity source code to analyse.
        contract_name: Human-readable contract name for the record.
        file_path: Logical file path used for logging context only.
        db: Active database session.
        request_id: Optional request ID for log correlation.

    Returns:
        ``ScanResponse`` with all findings and the DB-assigned scan ID.

    Raises:
        HTTPException: 500 if the analysis unexpectedly fails.
    """
    ctx = {"contract_name": contract_name, "file_path": file_path, "request_id": request_id}

    # -- Run analysis in thread pool (non-blocking) ----------------------------
    # asyncio.to_thread() runs the callable in the default ThreadPoolExecutor
    # so the event loop can serve other requests while Slither executes.
    with PerformanceTimer("analysis_pipeline", _scan_logger, extra=ctx):
        analysis_request = AnalysisScanRequest(
            source_code=source_code,
            contract_name=contract_name,
            file_path=file_path,
        )
        scan_result: ScanResult = await asyncio.to_thread(
            orchestrator.analyze, analysis_request
        )

    _scan_logger.info(
        "Analysis complete",
        extra={
            **ctx,
            "vulnerabilities_count": scan_result.vulnerabilities_count,
            "score": scan_result.overall_score,
        },
    )

    # -- Persist to DB (sync, but fast < 5 ms) --------------------------------
    with PerformanceTimer("db_persist_scan", _scan_logger, extra=ctx):
        findings_json = _findings_to_json(scan_result)
        scan_record = _build_scan_record(scan_result, findings_json)
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

    _scan_logger.info(
        "Scan persisted",
        extra={**ctx, "scan_id": scan_record.id},
    )

    return _scan_record_to_response(scan_record)


# ----------------------------------------------
# Endpoints
# ----------------------------------------------

@router.post("/scan", response_model=ScanResponse, summary="Scan contract source code")
@_conditional_rate_limit(per_minute=5, per_hour=20)
async def scan_contract(
    request: ScanRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    api_key: Optional[Any] = Depends(_api_key_dep()),
) -> ScanResponse:
    """
    Analyse a Solidity contract supplied as a JSON body.

    The endpoint sanitizes inputs, validates source length, runs the full
    analysis pipeline, persists results to the database, and returns a
    structured findings report.

    **Rate limits (unauthenticated):** 5 req/min · 20 req/hr

    Args:
        request: JSON body containing ``source_code`` and optional ``contract_name``.
        http_request: FastAPI ``Request`` object (used for request-ID correlation).
        db: Injected database session.
        api_key: Optional API key for elevated rate limits.

    Returns:
        ``ScanResponse`` with findings, scores, and a database scan ID.

    Raises:
        HTTPException: 400 for invalid input; 500 for unexpected failures.
    """
    request_id: str = getattr(http_request.state, "request_id", "")
    _scan_logger.info("Scan request received (JSON)", extra={"request_id": request_id})

    try:
        contract_name = request.contract_name or "UnnamedContract"
        source_code, contract_name = _sanitize_source(request.source_code, contract_name)
        _validate_source_length(source_code)

        return await _run_analysis_and_persist(
            source_code=source_code,
            contract_name=contract_name,
            file_path="api_upload",
            db=db,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {exc}",
        ) from exc
    except Exception as exc:
        log_error_context(
            _scan_logger,
            "Unexpected error during contract scan",
            exc,
            context={"request_id": request_id},
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Analysis failed. Please check your contract syntax and try again. "
                "If the problem persists, contact support."
            ),
        ) from exc


@router.post("/scan/file", response_model=ScanResponse, summary="Scan an uploaded .sol file")
@_conditional_rate_limit(per_minute=5, per_hour=20)
async def scan_contract_file(
    http_request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: Optional[Any] = Depends(_api_key_dep()),
) -> ScanResponse:
    """
    Analyse a Solidity contract supplied as a file upload (multipart/form-data).

    Validates the uploaded file (size, extension, MIME type when security is
    enabled), decodes UTF-8 content, then runs the same analysis pipeline as
    the JSON endpoint.

    **Rate limits (unauthenticated):** 5 req/min · 20 req/hr

    Args:
        http_request: FastAPI ``Request`` object (request-ID correlation).
        file: Uploaded ``.sol`` file.
        db: Injected database session.
        api_key: Optional API key for elevated rate limits.

    Returns:
        ``ScanResponse`` with findings, scores, and a database scan ID.

    Raises:
        HTTPException: 400 for validation failures; 500 for unexpected errors.
    """
    request_id: str = getattr(http_request.state, "request_id", "")
    filename: str = file.filename or "uploaded_file.sol"
    _scan_logger.info(
        "Scan request received (file upload)",
        extra={"request_id": request_id, "file_name": filename},
    )

    try:
        # Validate via security module if available
        if SECURITY_ENABLED:
            is_valid, error_message = await _file_validator.validate_file(file)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)

        # Read and decode file content
        raw_bytes: bytes = await file.read()
        try:
            source_code: str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "File encoding error: the uploaded file must be valid UTF-8 text. "
                    "Please save your Solidity file with UTF-8 encoding."
                ),
            ) from exc

        _validate_source_length(source_code)

        # Derive contract name from filename
        contract_name: str = filename.removesuffix(".sol") or "UnnamedContract"
        source_code, contract_name = _sanitize_source(source_code, contract_name)

        return await _run_analysis_and_persist(
            source_code=source_code,
            contract_name=contract_name,
            file_path=filename,
            db=db,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        log_error_context(
            _scan_logger,
            "Unexpected error during file scan",
            exc,
            context={"request_id": request_id, "file_name": filename},
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "File analysis failed. Please verify the file is a valid Solidity contract "
                "and try again."
            ),
        ) from exc


@router.get("/scans", response_model=List[ScanResponse], summary="List recent scans")
async def list_scans(
    http_request: Request,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    api_key: Optional[Any] = Depends(_api_key_dep()),
) -> List[ScanResponse]:
    """
    Return a paginated list of historical scans, newest first.

    Args:
        http_request: FastAPI ``Request`` object.
        skip: Number of records to skip (offset).
        limit: Maximum records to return (capped at 100).
        db: Injected database session.
        api_key: Optional API key.

    Returns:
        List of ``ScanResponse`` objects.

    Raises:
        HTTPException: 400 if ``limit`` > 100; 500 on database error.
    """
    request_id: str = getattr(http_request.state, "request_id", "")

    if limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit cannot exceed 100 items per page. Use 'skip' for pagination.",
        )

    try:
        with PerformanceTimer("db_list_scans", _scan_logger, extra={"request_id": request_id}):
            base_query = (
                db.query(Scan)
                .order_by(Scan.scanned_at.desc())
            )
            scans: List[Scan] = paginate(base_query, skip=skip, limit=limit)

        return [_scan_record_to_response(scan) for scan in scans]

    except HTTPException:
        raise
    except Exception as exc:
        log_error_context(
            _scan_logger,
            "Failed to retrieve scan list",
            exc,
            context={"request_id": request_id, "skip": skip, "limit": limit},
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve scans. Please try again later.",
        ) from exc


@router.get("/scans/{scan_id}", response_model=ScanResponse, summary="Get scan by ID")
async def get_scan(
    scan_id: int,
    http_request: Request,
    db: Session = Depends(get_db),
    api_key: Optional[Any] = Depends(_api_key_dep()),
) -> ScanResponse:
    """
    Retrieve a single scan record by its database ID.

    Args:
        scan_id: Primary key of the scan to fetch.
        http_request: FastAPI ``Request`` object.
        db: Injected database session.
        api_key: Optional API key.

    Returns:
        ``ScanResponse`` with full scan details and findings.

    Raises:
        HTTPException: 400 for invalid ID; 404 if not found; 500 on error.
    """
    request_id: str = getattr(http_request.state, "request_id", "")

    if scan_id < 1:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scan ID '{scan_id}'. ID must be a positive integer.",
        )

    try:
        with PerformanceTimer(
            "db_get_scan", _scan_logger, extra={"request_id": request_id, "scan_id": scan_id}
        ):
            scan: Optional[Scan] = get_by_id(db, Scan, scan_id)

        if scan is None:
            raise HTTPException(
                status_code=404,
                detail=f"Scan with ID {scan_id} was not found.",
            )

        return _scan_record_to_response(scan)

    except HTTPException:
        raise
    except Exception as exc:
        log_error_context(
            _scan_logger,
            "Failed to retrieve scan",
            exc,
            context={"request_id": request_id, "scan_id": scan_id},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve scan {scan_id}. Please try again later.",
        ) from exc


# ----------------------------------------------
# Delete endpoint (only registered when security is available)
# ----------------------------------------------
if SECURITY_ENABLED:  # pragma: no cover

    @router.delete("/scans/{scan_id}", summary="Delete a scan (requires API key)")
    async def delete_scan(
        scan_id: int,
        http_request: Request,
        db: Session = Depends(get_db),
        api_key: Any = Depends(get_optional_api_key),
    ) -> Dict[str, str]:
        """
        Permanently delete a scan record by ID.

        **Requires API key authentication.**

        Args:
            scan_id: Primary key of the scan to delete.
            http_request: FastAPI ``Request`` object.
            db: Injected database session.
            api_key: API key (required — request rejected without one).

        Returns:
            Confirmation message dict.

        Raises:
            HTTPException: 401 without API key; 404 if not found; 500 on error.
        """
        request_id: str = getattr(http_request.state, "request_id", "")

        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key is required to perform delete operations.",
            )

        try:
            scan: Optional[Scan] = get_by_id(db, Scan, scan_id)

            if scan is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Scan with ID {scan_id} was not found.",
                )

            db.delete(scan)
            db.commit()

            _scan_logger.info(
                "Scan deleted",
                extra={"request_id": request_id, "scan_id": scan_id},
            )
            return {"message": f"Scan {scan_id} deleted successfully."}

        except HTTPException:
            raise
        except Exception as exc:
            log_error_context(
                _scan_logger,
                "Failed to delete scan",
                exc,
                context={"request_id": request_id, "scan_id": scan_id},
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete scan {scan_id}. Please try again later.",
            ) from exc
