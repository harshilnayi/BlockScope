"""
Pydantic schemas for BlockScope scan API request and response payloads.

These schemas are used by FastAPI for:
- Automatic request body validation and parsing (``ScanRequest``).
- Response serialisation and OpenAPI documentation (``ScanResponse``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """
    Request body schema for the ``POST /scan`` endpoint.

    Attributes:
        source_code: Full Solidity source code of the contract to analyse.
            Must be between 10 and 500,000 characters.
        contract_name: Optional human-readable name for the contract.
            If omitted, the name is auto-detected from the source code.
    """

    source_code: str = Field(
        ...,
        min_length=10,
        max_length=500_000,
        description="Solidity contract source code (10 – 500,000 characters).",
        examples=["pragma solidity ^0.8.20;\n\ncontract SimpleStorage {\n    uint256 value;\n}"],
    )
    contract_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional display name for the contract.  Auto-detected if omitted.",
        examples=["SimpleStorage"],
    )

    model_config = {"str_strip_whitespace": True}


class FindingResponse(BaseModel):
    """
    Schema for a single vulnerability finding returned in the scan response.

    Attributes:
        title: Short displayable name of the vulnerability (e.g. ``"Reentrancy"``).
        description: Detailed explanation of the issue.
        severity: Severity level — one of ``critical``, ``high``, ``medium``,
            ``low``, or ``info``.
        line_number: Source-code line where the issue was detected, if available.
        recommendation: Optional suggested fix or mitigation.
    """

    title: str = Field(..., description="Short name of the vulnerability.")
    description: str = Field(..., description="Detailed description of the issue.")
    severity: str = Field(
        ...,
        description="Severity level: critical | high | medium | low | info.",
    )
    line_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Source-code line number where the issue was found.",
    )
    recommendation: Optional[str] = Field(
        default=None,
        description="Suggested remediation or mitigation strategy.",
    )


class ScanResponse(BaseModel):
    """
    Response schema returned by all scan and scan-retrieval endpoints.

    Attributes:
        scan_id: Database-assigned primary key for this scan record.
        contract_name: Name of the analysed contract.
        vulnerabilities_count: Total number of findings detected.
        severity_breakdown: Finding counts grouped by severity level.
        overall_score: Security score from 0 (most vulnerable) to 100 (safest).
        summary: One-line human-readable result summary.
        findings: Ordered list of individual vulnerability findings.
        timestamp: UTC datetime when the analysis was completed.
    """

    scan_id: int = Field(..., description="Unique database ID for this scan.", ge=1)
    contract_name: str = Field(..., description="Name of the scanned contract.")
    vulnerabilities_count: int = Field(
        ..., ge=0, description="Total number of detected vulnerabilities."
    )
    severity_breakdown: Dict[str, int] = Field(
        ...,
        description=(
            "Finding counts keyed by severity level. "
            "Keys: critical, high, medium, low, info."
        ),
    )
    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Security score from 0 (most vulnerable) to 100 (safest).",
    )
    summary: str = Field(
        ..., description="One-line result summary, e.g. '2 critical, 1 high — UNSAFE [FAIL]'."
    )
    findings: List[FindingResponse] = Field(
        default_factory=list,
        description="Individual vulnerability findings, ordered by descending severity.",
    )
    timestamp: datetime = Field(
        ..., description="UTC datetime at which the analysis was completed."
    )

    model_config = {"from_attributes": True}
